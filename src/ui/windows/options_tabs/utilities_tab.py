import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from config.path_helpers import os_darwin, os_linux, os_windows
from patch_patterns.patterns import get_patterns_config_remote
from thread_utils import Threader
from utils.platform import open_in_file_manager

from ...utils import find_game_path, prompt_install_dir, restore_window_focus
from ..welcome_dialog import WelcomeDialog
from .base import OptionsContext, OptionsTab
from .shared_widgets.game_combobox import GameComboBox

log = logging.getLogger("Patch Config")


class UtilitiesTab(OptionsTab):
    """General app settings and helper tools."""

    title = "General Utilities"

    def __init__(self, context: OptionsContext, parent=None):
        super().__init__(context, parent)

        self.active_threads: list[Threader] = []
        font = self.ctx.font

        utilities_tab_layout = QVBoxLayout(self)
        utilities_tab_layout.setContentsMargins(10, 10, 10, 10)
        utilities_tab_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Title ---
        title_label = QLabel("<b>General Utilities</b>")
        title_label.setFont(font)
        utilities_tab_layout.addWidget(title_label)

        # --- Description Label
        desc_label = QLabel("Additional tools and utilities for game management.")
        desc_label.setWordWrap(True)
        utilities_tab_layout.addWidget(desc_label)

        # --- Selected Game Dropdown ---
        # Game-specific buttons below act on whichever game is selected here.
        selected_game_layout = QHBoxLayout()
        selected_game_label = QLabel("Game:")
        selected_game_label.setObjectName("UtilitiesGameLabel")
        selected_game_label.setFont(font)
        self.utilities_selected_game_combobox = GameComboBox(self.ctx)
        self.utilities_selected_game_combobox.setObjectName("UtilitiesGameCombobox")
        self.utilities_selected_game_combobox.setToolTip("Game that the utilities below act on.")
        selected_game_layout.addWidget(selected_game_label)
        selected_game_layout.addWidget(self.utilities_selected_game_combobox)
        selected_game_layout.addStretch()
        utilities_tab_layout.addLayout(selected_game_layout)

        # --- Scroll Area ---
        utilities_scroll_area = QScrollArea()
        utilities_scroll_area.setWidgetResizable(True)

        # --- Scrollable Content Widget
        utilities_content_widget = QWidget()
        utilities_layout = QVBoxLayout(utilities_content_widget)
        utilities_layout.setContentsMargins(5, 5, 5, 5)
        utilities_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Fetch/Update Patterns File Button ---
        btn_update_patch_patterns = QPushButton("Update Patterns")
        btn_update_patch_patterns.setFont(font)
        btn_update_patch_patterns.clicked.connect(self.fetch_patch_patterns)
        utilities_layout.addWidget(btn_update_patch_patterns)

        # --- Show Game Folder Button ---
        btn_show_game_folder = QPushButton("Show Game Folder")
        btn_show_game_folder.setFlat(False)
        btn_show_game_folder.setFont(font)
        btn_show_game_folder.clicked.connect(lambda: self.show_game_folder())
        utilities_layout.addWidget(btn_show_game_folder)

        # --- Show Save Games Folder Button ---
        btn_show_save_games_folder = QPushButton("Show Save Games Folder")
        btn_show_save_games_folder.setFlat(False)
        btn_show_save_games_folder.setFont(font)
        btn_show_save_games_folder.clicked.connect(self.show_save_games_folder)
        utilities_layout.addWidget(btn_show_save_games_folder)

        # --- Open Config Directory Button ---
        btn_show_app_config_dir = QPushButton("Show App Config Folder")
        btn_show_app_config_dir.setFont(font)
        btn_show_app_config_dir.clicked.connect(self.show_app_config_folder)
        utilities_layout.addWidget(btn_show_app_config_dir)

        # --- Steam Validate Game Files Button ---
        btn_validate_game_files = QPushButton("Validate Integrity of Game Files (Steam)")
        btn_validate_game_files.setFont(font)
        btn_validate_game_files.setToolTip("Trigger the validation of game files through Steam.")
        btn_validate_game_files.clicked.connect(self._validate_steam_game_files)
        utilities_layout.addWidget(btn_validate_game_files)

        # --- Open Welcome Dialog Button ---
        btn_show_welcome_dialog = QPushButton("Show Welcome Dialog")
        btn_show_welcome_dialog.setFont(font)
        btn_show_welcome_dialog.clicked.connect(self.show_welcome_dialog)
        utilities_layout.addWidget(btn_show_welcome_dialog)

        # --- Maximum Allowed Backups ---
        max_backups_control_layout = QHBoxLayout()

        # Maximum Backups Label
        max_backups_label = QLabel("Maximum Backups:")
        max_backups_label.setFont(font)
        max_backups_label.setToolTip(
            "Define the maximum number of backup files to keep for the game binary. Set to 0 to disable backups."
        )

        # Maximum Backups Slider
        self.max_backups_slider = QSlider(Qt.Horizontal)
        self.max_backups_slider.setMinimum(0)
        self.max_backups_slider.setMaximum(10)  # Reasonable max allowed backups
        self.max_backups_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.max_backups_slider.setTickInterval(1)
        self.max_backups_slider.setToolTip("Drag to adjust maximum number of backups.")
        self.max_backups_slider.valueChanged.connect(self._on_max_backups_slider_changed)

        # Value Display Label
        self.max_backup_value_label = QLabel()
        self.max_backup_value_label.setFont(font)
        self.max_backup_value_label.setMaximumWidth(70)
        self.max_backup_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add widgets
        max_backups_control_layout.addWidget(max_backups_label)
        max_backups_control_layout.addWidget(self.max_backup_value_label)
        max_backups_control_layout.addWidget(self.max_backups_slider, 1)
        utilities_layout.addLayout(max_backups_control_layout)

        # --- Use Local Patterns Checkbox---
        self.chkbox_use_local_patterns = QCheckBox("Force Local Patterns")
        self.chkbox_use_local_patterns.setToolTip(
            "When toggled, application will not longer pull updated patterns from remote and will only strictly use the patterns file present on disk.\nThis is mainly useful for testing purposes, for trying out different patterns to prevent the local file from being overwritten on application startup."
        )
        self.chkbox_use_local_patterns.stateChanged.connect(self.callback_use_local_patterns)
        # Force update state when global enforcement rule is applied
        if any((self.svc.config.use_local_patterns, self.svc.config.prevent_conn)):
            self.chkbox_use_local_patterns.setEnabled(False)
        utilities_layout.addWidget(self.chkbox_use_local_patterns)

        # --- Spacer ---
        utilities_layout.addStretch()

        # --- Set scrollable widget ---
        utilities_scroll_area.setWidget(utilities_content_widget)
        utilities_tab_layout.addWidget(utilities_scroll_area)

    # --- OptionsTab hooks ---

    def load(self):
        log.info("Load Settings")
        self.utilities_selected_game_combobox.populate()

        # Backups slider (no signal: value comes from settings, nothing to save)
        max_backups = self.svc.settings.settings.max_allowed_binary_backups
        self.max_backups_slider.blockSignals(True)
        self.max_backups_slider.setValue(max_backups)
        self.max_backups_slider.blockSignals(False)
        self._update_max_backups_label(max_backups)

        # Reflect settings in UI
        use_local_patterns = any(
            [
                self.svc.config.use_local_patterns,
                self.svc.config.prevent_conn,
                self.svc.settings.settings.force_local_patterns,
            ]
        )
        self.chkbox_use_local_patterns.setCheckState(
            Qt.CheckState.Checked if use_local_patterns else Qt.CheckState.Unchecked
        )

    def cleanup(self):
        """Stop any running worker threads."""
        for thread in self.active_threads:
            if thread.isRunning():
                thread.quit()
                thread.wait()
            thread.deleteLater()
        self.active_threads.clear()

    # --- Helpers ---

    @property
    def selected_game(self) -> Optional[str]:
        """Game picked in the dropdown, which game-specific utilities act on."""
        return self.config.game if self.config else None

    def _update_max_backups_label(self, value: int):
        self.max_backup_value_label.setText("Off" if value <= 0 else str(value))

    # --- Slots ---

    def _validate_steam_game_files(self):
        game = self.selected_game
        if not game:
            log.warning("No game selected. Unable to validate game files.")
            return

        install_path = self.svc.settings.game(game).install_path
        app_id = self.svc.steam_helper.get_app_id_from_install_path(install_path)

        # Remove the binary file before verifying
        game_binary = Path(install_path)
        if game_binary.exists() and game_binary.is_file():
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
            return None

        paths = [
            self.svc.settings.game(game).install_path,
            self.svc.settings.game(game).proton_install_path,
        ]

        # Attempt to find a valid executable from settings
        saved_path = None

        # Prioritise auto_located_path
        if auto_located_path and auto_located_path.exists():
            saved_path = auto_located_path
            log.info(f"Using auto-located: {saved_path}", silent=True)

            # Save the paths
            if saved_path and saved_path.exists():
                saved_path_posix = saved_path.resolve().as_posix()
                log.info(f"Save: '{saved_path_posix}'")

                if os_windows():
                    self.svc.settings.game(game).install_path = saved_path_posix
                elif (os_linux() and self.svc.config.use_proton) or (os_linux() and self.config.is_proton):
                    self.svc.settings.game(game).proton_install_path = saved_path_posix
                else:
                    # Also account for proton cases
                    if self.config.is_proton:
                        self.svc.settings.game(game).proton_install_path = saved_path_posix
                    else:
                        self.svc.settings.game(game).install_path = saved_path_posix

        else:
            # Iterate once to test if any path exists
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
            # MacOS specific case
            if os_darwin():
                if saved_path.is_file():
                    saved_path = saved_path.parent.parent.parent

            log.info(f"Opening game folder: '{saved_path}'", silent=False)
            open_in_file_manager(saved_path)
            return saved_path
        else:
            log.warning(f"Unable to determine saved path: '{saved_path}'")
            log.info("Attempting to auto-locate game installation...")

            if not auto_located_path and not _retry_attempted:
                # Attempt to auto locate and re-run the function
                path_finder_thread = Threader(target=self._find_game_path_worker_thread)
                path_finder_thread.signals.result.connect(
                    lambda result: self.show_game_folder(result, _retry_attempted=True)
                )
                path_finder_thread.signals.finished.connect(lambda: self._cleanup_thread(path_finder_thread))
                self.active_threads.append(path_finder_thread)
                path_finder_thread.start()
                return None
            else:
                log.info("Auto-location already attempted and failed.", silent=True)
                picked_path = prompt_install_dir(game)

                if picked_path:
                    self.show_game_folder(auto_located_path=picked_path, _retry_attempted=_retry_attempted)
                if not picked_path:
                    # User cancelled
                    log.warning(f"User cancelled location. Aborting patch")
                    return None

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

    def _on_max_backups_slider_changed(self, value: int):
        self._update_max_backups_label(value)

        # Save to settings
        self.svc.settings.settings.max_allowed_binary_backups = value

        log.info(f"Maximum allowed backups set to: {value}")

    def callback_use_local_patterns(self, state):
        if state in (Qt.CheckState.Checked.value, Qt.CheckState.Unchecked.value):
            # We don't need to set for --no-conn
            if not self.svc.config.prevent_conn:
                self.svc.settings.settings.force_local_patterns = bool(state)
        else:
            log.warning("Checkbox in Partially Checked state. We shouldn't be here.", silent=True)

    def show_app_config_folder(self):
        config_dir = self.svc.config.config_dir

        if config_dir.exists() and config_dir.is_dir():
            log.info(f"App Config Folder: {config_dir}", silent=True)

            open_in_file_manager(config_dir)

    def fetch_patch_patterns(self):
        log.info(f"Fetch Patch Patterns...", silent=True)

        get_patterns_config_remote()

        self.ctx.patcher.reload_patterns()

        # New patterns may change games/versions/patches: reload every tab
        self.ctx.reload_requested.emit()

    def show_welcome_dialog(self):
        dialog = self.window()
        welcome_dialog = WelcomeDialog(self.ctx.font, window_icon=dialog.windowIcon(), parent=dialog)
        welcome_dialog.show()
