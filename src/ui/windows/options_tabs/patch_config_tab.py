import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app_ids import APP_IDS
from config.path_helpers import os_darwin, os_linux
from patchers import PatchConfiguration
from patchers import models as patcher_models
from thread_utils import Threader
from utils.helpers import (
    block_signals,
    delete_fpaths,
    find_binary_backups,
    format_size,
    get_fpath_size,
)
from utils.platform import open_in_file_manager

from ...utils import find_game_path, prompt_install_dir, restore_window_focus
from .base import OptionsContext, OptionsTab
from .shared_widgets.game_combobox import GameComboBox

log = logging.getLogger("Patch Config")


class GameUtilitiesTab(OptionsTab):
    """Game/version/platform selection, the list of patches to apply and game-specific actions."""

    title = "Game Utilities"

    def __init__(self, context: OptionsContext, parent=None):
        super().__init__(context, parent)

        self.active_threads: list[Threader] = []

        font = self.ctx.font

        patch_layout = QVBoxLayout(self)
        patch_layout.setContentsMargins(10, 10, 10, 10)

        # --- Game Info Section ---
        info_label = QLabel("<b>Patch Configuration</b>")
        info_label.setFont(font)
        patch_layout.addWidget(info_label)

        desc_label = QLabel("Select what game to patch and with that options.")
        desc_label.setWordWrap(True)
        patch_layout.addWidget(desc_label)

        # --- Game & Version Selection ---
        selection_layout = QHBoxLayout()

        self.game_combobox = GameComboBox(self.ctx)

        self.version_combobox = QComboBox()
        self.version_combobox.setFont(font)
        self.version_combobox.setMaximumWidth(140)

        selection_layout.addWidget(QLabel("Game:"))
        selection_layout.addWidget(self.game_combobox)
        selection_layout.addWidget(QLabel("Version:"))
        selection_layout.addWidget(self.version_combobox, 1)
        patch_layout.addLayout(selection_layout)

        # --- Native/Proton Dropdown (Linux/macOS) ---
        # Each item carries the platform of the binary it patches
        self.platform_picker = QComboBox()
        if os_linux() or os_darwin():
            self.platform_picker.addItem(
                patcher_models.TRANSLATION_LAYER_ENUM.NATIVE, patcher_models.Platform.detect_current().value
            )
            self.platform_picker.addItem(
                patcher_models.TRANSLATION_LAYER_ENUM.PROTON, patcher_models.Platform.WINDOWS.value
            )
            self.platform_picker.setFont(font)
            self.platform_picker.setMinimumWidth(100)
            selection_layout.addWidget(self.platform_picker)

        # --- Patches Area (Scrollable) ---
        self.patches_scroll_area = QScrollArea()
        self.patches_scroll_area.setWidgetResizable(True)
        self.patches_scroll_area.setMinimumHeight(200)

        self.patches_widget = QWidget()

        self.patches_layout = QVBoxLayout(self.patches_widget)
        self.patches_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.patches_scroll_area.setWidget(self.patches_widget)
        patch_layout.addWidget(self.patches_scroll_area)

        # --- Game-specific actions (act on the selected game) ---
        utilities_layout = QVBoxLayout()
        patch_layout.addLayout(utilities_layout)

        # === Show X Folder Buttons Layout ===
        show_x_folder_buttons_layout = QHBoxLayout()
        utilities_layout.addLayout(show_x_folder_buttons_layout)

        # --- Show Save Games Folder Button ---
        btn_show_save_games_folder = QPushButton("Show Save Games Folder")
        btn_show_save_games_folder.setFlat(False)
        btn_show_save_games_folder.setFont(font)
        btn_show_save_games_folder.clicked.connect(self.show_save_games_folder)
        show_x_folder_buttons_layout.addWidget(btn_show_save_games_folder)

        # --- Show Game Folder Button ---
        btn_show_game_folder = QPushButton("Show Game Folder")
        btn_show_game_folder.setFlat(False)
        btn_show_game_folder.setFont(font)
        # Lambda drops the `checked` argument from clicked()
        btn_show_game_folder.clicked.connect(lambda: self.show_game_folder())
        show_x_folder_buttons_layout.addWidget(btn_show_game_folder)

        # ===========================================

        # --- Steam Validate Game Files Button ---
        btn_validate_game_files = QPushButton("Validate Integrity of Game Files (Steam)")
        btn_validate_game_files.setFont(font)
        btn_validate_game_files.setToolTip("Trigger the validation of game files through Steam.")
        btn_validate_game_files.clicked.connect(self.validate_steam_game_files)
        utilities_layout.addWidget(btn_validate_game_files)

        # --- Delete Binary Backups Button ---
        btn_delete_binary_backups = QPushButton("Delete Backups")
        btn_delete_binary_backups.setFont(font)
        btn_delete_binary_backups.setToolTip("Delete generated backups of the game executable made when patching.")
        btn_delete_binary_backups.clicked.connect(self.delete_binary_backups)
        utilities_layout.addWidget(btn_delete_binary_backups)

        # --- Signals ---
        # Every control writes its change into the shared configuration straight away.
        # Game can be picked here or in another tab, so it arrives through the context.
        self.ctx.game_changed.connect(self._on_game_changed)
        self.version_combobox.currentIndexChanged.connect(self._on_version_changed)
        self.platform_picker.currentIndexChanged.connect(self._on_platform_changed)

    # --- OptionsTab hooks ---

    def load(self):
        log.info("Populating Options", silent=True)

        if not self._is_valid(self.config):
            log.warning(f"Invalid configuration, creating default: {self.config}")
            self.config = PatchConfiguration.create_default(self.ctx.patcher)
            if not self.config:
                log.error("Failed to create a default configuration")
                return

        self.config.platform = (
            patcher_models.Platform.parse(self.config.platform) or patcher_models.Platform.detect_current()
        )

        self.game_combobox.populate()
        self._on_game_changed(self.config.game)

    def cleanup(self):
        """Stop any running worker threads."""
        for thread in self.active_threads:
            if thread.isRunning():
                thread.quit()
                thread.wait()
            thread.deleteLater()
        self.active_threads.clear()

    # --- Slots ---

    def _on_game_changed(self, game: str):
        """Show the platform, versions and patches for the selected game."""
        # Restore the Native/Proton choice last patched with for this game
        saved_platform = self._saved_platform(game)
        if saved_platform:
            self.config.platform = saved_platform
        self._show_platform()

        # Keep the configured version if it still applies, otherwise let the patcher choose.
        # (Changing game resets the configured version, see OptionsContext.select_game.)
        picked_version = self.ctx.patcher.pick_version(
            game, platform=self.config.platform, preferred=self.config.version
        )
        if picked_version:
            self.config.version = picked_version
        else:
            log.warning(f"No version with patches available for {game} on {self.config.platform}")
        self._show_versions(game)

        self._rebuild_patches()

    def _on_version_changed(self, index: int):
        if index < 0:
            return
        self.config.version = self.version_combobox.itemData(index)
        self._rebuild_patches()

    def _on_platform_changed(self, index: int):
        if index < 0:
            return
        platform = patcher_models.Platform(self.platform_picker.itemData(index))
        log.info(f"Binary platform changed to: {platform}", silent=True)
        self.config.platform = platform
        self._rebuild_patches()

    def _on_patch_toggled(self, patch_name: str, checked: bool):
        selected = self.config.selected_patches
        if checked and patch_name not in selected:
            selected.append(patch_name)
        elif not checked and patch_name in selected:
            selected.remove(patch_name)

    def validate_steam_game_files(self):
        game = self.selected_game
        if not game:
            log.warning("No game selected. Unable to validate game files.")
            return

        install_path = self._saved_install_path(game)
        app_id = self._steam_app_id(game, install_path)

        # Don't touch any files unless Steam can actually restore them
        if not app_id:
            log.error(f"Unable to determine Steam App ID for '{game}'. Validation aborted.")
            return

        # Remove the binary file before verifying, so Steam restores an unmodified copy
        if install_path:
            game_binary = Path(install_path)
            if game_binary.is_file():
                log.info(f"Removing game binary before verifying: {game_binary}")
                try:
                    game_binary.unlink()
                except Exception as e:
                    log.error(f"Failed to unlink game binary: {e}")

        self.svc.steam_helper.validate_game_files_app_id(app_id)

        try:
            dialog = self.window()
            main_window = dialog.parent() if dialog.parent() else dialog
            restore_window_focus(main_window)
        except Exception as e:
            log.error(f"Error restoring window focus: {e}")

    def show_game_folder(self, auto_located_path: Optional[Path] = None, _retry_attempted: bool = False):
        game = self.selected_game
        if not game:
            log.warning("No game selected. Unable to locate game folder.")
            return

        paths = [
            self.svc.settings.game(game).install_path,
            self.svc.settings.game(game).proton_install_path,
        ]

        saved_path = None

        # Prioritise auto_located_path
        if auto_located_path and auto_located_path.exists():
            saved_path = auto_located_path
            log.info(f"Using auto-located: {saved_path}", silent=True)

            # Save the path for next time
            saved_path_posix = saved_path.resolve().as_posix()
            log.info(f"Save: '{saved_path_posix}'")

            if self.config.is_proton:
                self.svc.settings.game(game).proton_install_path = saved_path_posix
            else:
                self.svc.settings.game(game).install_path = saved_path_posix

        else:
            # Use the first saved path (or its folder) that exists
            for path_str in paths:
                if not path_str:
                    continue

                path = Path(path_str)

                if path.exists():
                    saved_path = path
                    log.info(f"Saved path: '{saved_path}'", silent=True)
                    break

                if path.parent.exists():
                    saved_path = path.parent
                    log.info(f"Derived Game Folder: {saved_path}", silent=True)
                    break

        if saved_path:
            # macOS: go from the binary inside the .app bundle to the game folder
            if os_darwin() and saved_path.is_file():
                saved_path = saved_path.parent.parent.parent

            log.info(f"Opening game folder: '{saved_path}'", silent=False)
            open_in_file_manager(saved_path)
            return

        log.warning(f"Unable to determine game folder for '{game}'.")

        if not auto_located_path and not _retry_attempted:
            # Auto-locate in the background, then try again with the result
            log.info("Attempting to auto-locate game installation...")
            path_finder_thread = Threader(target=self._find_game_path_worker_thread)
            path_finder_thread.signals.result.connect(
                lambda result: self.show_game_folder(result, _retry_attempted=True)
            )
            path_finder_thread.signals.finished.connect(lambda: self._cleanup_thread(path_finder_thread))
            self.active_threads.append(path_finder_thread)
            path_finder_thread.start()
            return

        log.info("Auto-location already attempted and failed.", silent=True)
        picked_path = prompt_install_dir(game)

        if picked_path:
            self.show_game_folder(auto_located_path=picked_path, _retry_attempted=_retry_attempted)
        else:
            log.warning("User cancelled location. Unable to show game folder.")

    def show_save_games_folder(self):
        game = self.selected_game

        if not game:
            log.warning("No game selected. Unable to locate save games folder.")
            return

        saved = self.svc.settings.game(game).save_games_folder
        save_games_path = Path(saved) if saved else None

        if not save_games_path or not save_games_path.is_dir():
            from patchers.save_patcher import SavePatcher

            located = SavePatcher(game).save_games_folders
            save_games_path = located[0] if located else None  # TODO: Selection picker

            if save_games_path:
                self.svc.settings.game(game).save_games_folder = save_games_path.as_posix()

        if not save_games_path:
            log.warning(f"Could not find a save games folder for {game}.")
            return

        log.info(f"Opening save games folder: {save_games_path}", silent=True)
        open_in_file_manager(save_games_path)

    def delete_binary_backups(self):
        game = self.selected_game
        if not game:
            log.warning("No game selected. Unable to delete executable backups.")
            return

        # Backups of both the native and Proton executables
        game_settings = self.svc.settings.game(game)
        binary_paths = [Path(p) for p in (game_settings.install_path, game_settings.proton_install_path) if p]

        if not binary_paths:
            log.warning(f"No saved executable location for {game}. Unable to look for backups.")
            self._show_message(
                "No Game Location",
                f"Couldn't find where {game} executable is yet.\n\n" "Patch the game or use Show Game Folder first.",
            )
            return

        backups = sorted({b for path in binary_paths for b in find_binary_backups(path)})

        if not backups:
            log.info(f"No executable backups found for {game}.")
            self._show_message("No Backups", f"No backups of the {game} executable were found.")
            return

        total_size = sum(get_fpath_size(b) for b in backups)

        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Icon.Question)
        confirm.setWindowTitle("Delete Executable Backups")
        confirm.setText(
            f"Delete {len(backups)} backup(s) of the {game} executable ({format_size(total_size)})?\n\n"
            "This can't be undone."
        )
        confirm.setDetailedText("\n".join(str(b) for b in backups))
        confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm.setDefaultButton(QMessageBox.StandardButton.No)

        if confirm.exec() != QMessageBox.StandardButton.Yes:
            log.info("Deleting executable backups cancelled.", silent=True)
            return

        deleted, failed = delete_fpaths(backups)
        log.info(f"Deleted {len(deleted)} of {len(backups)} {game} executable backup(s).")

        if failed:
            self._show_message(
                "Some Backups Not Deleted",
                f"Deleted {len(deleted)} backup(s), but {len(failed)} could not be deleted:\n\n"
                + "\n".join(str(f) for f in failed),
                icon=QMessageBox.Icon.Warning,
            )
        else:
            self._show_message("Backups Deleted", f"Deleted {len(deleted)} backup(s) of the {game} executable.")

    # --- Helpers ---

    def _show_message(self, title: str, text: str, icon: QMessageBox.Icon = QMessageBox.Icon.Information):
        msgbox = QMessageBox(self)
        msgbox.setIcon(icon)
        msgbox.setWindowTitle(title)
        msgbox.setText(text)
        msgbox.exec()

    def _is_valid(self, config: Optional[PatchConfiguration]) -> bool:
        return bool(config and config.version and config.game in self.ctx.patcher.get_available_games())

    def _saved_platform(self, game: str) -> Optional[patcher_models.Platform]:
        """Platform last patched for `game`, if one was saved and is valid."""
        saved = self.svc.settings.game(game).patched_platform
        platform = patcher_models.Platform.parse(saved)
        if saved and not platform:
            log.warning(f"Invalid saved platform '{saved}' for {game}. Ignoring.")
        return platform

    def _show_platform(self):
        """Select the configured platform in the Native/Proton picker (Linux/macOS only)."""
        index = self.platform_picker.findData(self.config.platform.value)
        if index >= 0:
            with block_signals(self.platform_picker):
                self.platform_picker.setCurrentIndex(index)

    def _show_versions(self, game: str):
        """Fill the version dropdown for `game` and select the configured version."""
        with block_signals(self.version_combobox):
            self.version_combobox.clear()
            for version in self.ctx.patcher.get_available_versions(game):
                # Show a tidy name ("Latest"), keep the patterns key ("latest") as the item's data
                label = version.capitalize() if " " not in version else version.title()
                self.version_combobox.addItem(label, version)
            self.version_combobox.setCurrentIndex(max(self.version_combobox.findData(self.config.version), 0))

    def _rebuild_patches(self):
        """Show a checkbox per patch for the configured game, version and platform."""
        while self.patches_layout.count():
            child = self.patches_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        patcher = self.ctx.patcher.get_game_patcher(self.config.game, self.config.version)
        if not patcher:
            return

        available_patches = patcher.get_available_patches(platform=self.config.platform)

        # No selection yet (e.g. game just changed): start from the defaults
        selected = self.config.selected_patches or [
            name for name, patch in available_patches.items() if patch.enabled or patch.required
        ]

        for patch_name, patch_info in available_patches.items():
            checkbox = QCheckBox(patch_info.display_name)
            checkbox.setToolTip(patch_info.description)
            checkbox.setFont(self.ctx.font)
            checkbox.setChecked(patch_info.required or patch_name in selected)
            checkbox.setDisabled(patch_info.required)  # Required patches can't be turned off
            checkbox.toggled.connect(lambda checked, name=patch_name: self._on_patch_toggled(name, checked))
            self.patches_layout.addWidget(checkbox)

        # Selection is exactly what's ticked for this game/version/platform
        self.config.selected_patches = [
            name for name, patch in available_patches.items() if patch.required or name in selected
        ]

        log.info(
            f"Showing patches for {self.config.game} '{self.config.version}' on {self.config.platform}: "
            f"{self.config.selected_patches}",
            silent=True,
        )

    def _saved_install_path(self, game: str) -> Optional[str]:
        """Saved game binary path for the selected binary type (native or Proton)."""
        game_settings = self.svc.settings.game(game)
        return game_settings.proton_install_path if self.config.is_proton else game_settings.install_path

    def _steam_app_id(self, game: str, install_path: Optional[str]) -> Optional[str]:
        """Steam App ID from the game's install folder, falling back to the known App IDs."""
        app_id = self.svc.steam_helper.get_app_id_from_install_path(install_path) if install_path else None

        if not app_id or app_id == "-1":
            known_id = APP_IDS.get(game.lower())
            app_id = str(known_id) if known_id else None

        return app_id

    def _find_game_path_worker_thread(self) -> Optional[Path]:
        """
        WORKER FUNCTION: Tries to find the game path automatically.
        Returns the path if found, otherwise None.
        """
        return find_game_path(self.ctx.patcher, self.config)

    def _cleanup_thread(self, thread: Threader):
        """Remove finished thread from active list."""
        if thread in self.active_threads:
            self.active_threads.remove(thread)
            thread.deleteLater()
            log.info(f"Cleaned up worker thread. Active threads: {len(self.active_threads)}", silent=True)
