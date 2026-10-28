import logging
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from app_services import services
from patchers.save_patcher import SaveBackup, find_save_backups
from utils.helpers import block_signals, delete_fpaths, format_size
from utils.platform import open_in_file_manager

log = logging.getLogger("Save Backups")

COLUMN_BACKUP = 0
COLUMN_FILES = 1
COLUMN_SIZE = 2


class SaveBackupsDialog(QDialog):
    """
    Lists the save backups made when fixing saves, grouped by playthrough, and deletes the ones the user ticks.

    Opens with all unticked so everything is kept unless user specifically picks it.
    """

    # Share of the screen the dialog opens at, and the smallest size that still fits every button
    SCREEN_FRACTION = (0.45, 0.6)
    MIN_SIZE = QSize(560, 360)

    def __init__(self, font: QFont, parent=None):
        super().__init__(parent)

        self.backups_dir: Path = services().config.saves_backup_dir

        # Every backup row in the tree, with the backup it shows
        self._rows: list[tuple[QTreeWidgetItem, SaveBackup]] = []

        self.setObjectName("SaveBackupsDialog")
        self.setWindowTitle("Manage Save Backups")
        self.setFont(font)
        self._fit_to_screen(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        desc_label = QLabel(
            "Backups made each time a save is fixed, grouped by playthrough.\n"
            "Tick the backups to delete. Anything left unticked is kept. "
            "Your saves in the game's save games folder are not affected."
        )
        desc_label.setObjectName("SaveBackupsDescription")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # --- Backups Tree ---
        self.tree = QTreeWidget()
        self.tree.setObjectName("SaveBackupsTree")
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Backup", "Save File", "Size"])
        self.tree.setUniformRowHeights(True)
        header = self.tree.header()
        header.setSectionResizeMode(COLUMN_BACKUP, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COLUMN_FILES, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COLUMN_SIZE, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(False)
        self.tree.itemChanged.connect(self._update_summary)
        layout.addWidget(self.tree, 1)

        # --- Selection Shortcuts ---
        selection_layout = QHBoxLayout()

        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.clicked.connect(lambda: self._set_all_checked(True))
        selection_layout.addWidget(self.btn_select_all)

        self.btn_select_none = QPushButton("Select None")
        self.btn_select_none.clicked.connect(lambda: self._set_all_checked(False))
        selection_layout.addWidget(self.btn_select_none)

        self.btn_keep_newest = QPushButton("Keep Newest Only")
        self.btn_keep_newest.setToolTip("Select every backup except the newest one of each playthrough.")
        self.btn_keep_newest.clicked.connect(self._select_all_but_newest)
        selection_layout.addWidget(self.btn_keep_newest)

        btn_show_folder = QPushButton("Show Backups Folder")
        btn_show_folder.clicked.connect(self._show_backups_folder)
        selection_layout.addWidget(btn_show_folder)

        layout.addLayout(selection_layout)

        # --- Summary ---
        self.summary_label = QLabel()
        self.summary_label.setObjectName("SaveBackupsSummary")
        layout.addWidget(self.summary_label)

        # --- Actions ---
        actions_layout = QHBoxLayout()
        actions_layout.addStretch(1)

        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.clicked.connect(self._delete_selected)
        actions_layout.addWidget(self.btn_delete)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        actions_layout.addWidget(btn_close)

        layout.addLayout(actions_layout)

        self.refresh()

    def _fit_to_screen(self, parent=None):
        """Open at a share of the screen the parent is on, never smaller than `MIN_SIZE` or larger than the screen."""
        screen = parent.screen() if parent else QApplication.primaryScreen()
        available = screen.availableGeometry().size()

        self.setMinimumSize(self.MIN_SIZE.boundedTo(available))

        width_fraction, height_fraction = self.SCREEN_FRACTION
        size = QSize(int(available.width() * width_fraction), int(available.height() * height_fraction))
        self.resize(size.expandedTo(self.minimumSize()).boundedTo(available))

    # --- Tree ---

    def refresh(self):
        """Read the backups folder again and rebuild the tree. Ticks are cleared."""
        backups_by_playthrough = find_save_backups(self.backups_dir)

        self._rows.clear()

        with block_signals(self.tree):
            self.tree.clear()

            for playthrough, backups in backups_by_playthrough.items():
                playthrough_item = QTreeWidgetItem(self.tree)
                playthrough_item.setText(COLUMN_BACKUP, playthrough)
                playthrough_item.setText(COLUMN_FILES, f"{len(backups)} backup(s)")
                playthrough_item.setText(COLUMN_SIZE, format_size(sum(b.size for b in backups)))
                playthrough_item.setTextAlignment(COLUMN_SIZE, Qt.AlignmentFlag.AlignRight)
                # Ticking a playthrough ticks all its backups, and it shows partly ticked when only some are
                playthrough_item.setFlags(
                    playthrough_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate
                )
                playthrough_item.setCheckState(COLUMN_BACKUP, Qt.CheckState.Unchecked)

                for backup in backups:
                    backup_item = QTreeWidgetItem(playthrough_item)
                    backup_item.setText(COLUMN_BACKUP, backup.created.strftime("%Y-%m-%d %H:%M:%S"))
                    backup_item.setText(COLUMN_FILES, ", ".join(f.name for f in backup.files) or "(empty)")
                    backup_item.setText(COLUMN_SIZE, format_size(backup.size))
                    backup_item.setTextAlignment(COLUMN_SIZE, Qt.AlignmentFlag.AlignRight)
                    backup_item.setToolTip(COLUMN_BACKUP, str(backup.folder))
                    backup_item.setToolTip(COLUMN_FILES, str(backup.folder))
                    backup_item.setFlags(backup_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    backup_item.setCheckState(COLUMN_BACKUP, Qt.CheckState.Unchecked)
                    self._rows.append((backup_item, backup))

            self.tree.expandAll()

        log.info(f"Found {len(self._rows)} save backup(s) in {len(backups_by_playthrough)} playthrough(s).")

        has_backups = bool(self._rows)
        for button in (self.btn_select_all, self.btn_select_none, self.btn_keep_newest):
            button.setEnabled(has_backups)

        self._update_summary()

    def _selected_backups(self) -> list[SaveBackup]:
        return [backup for item, backup in self._rows if item.checkState(COLUMN_BACKUP) == Qt.CheckState.Checked]

    def _set_all_checked(self, checked: bool):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        with block_signals(self.tree):
            for item, _ in self._rows:
                item.setCheckState(COLUMN_BACKUP, state)
        self._update_summary()

    def _select_all_but_newest(self):
        with block_signals(self.tree):
            for i in range(self.tree.topLevelItemCount()):
                playthrough_item = self.tree.topLevelItem(i)
                # Backups are listed newest first
                for child in range(playthrough_item.childCount()):
                    state = Qt.CheckState.Unchecked if child == 0 else Qt.CheckState.Checked
                    playthrough_item.child(child).setCheckState(COLUMN_BACKUP, state)
        self._update_summary()

    def _update_summary(self, *_):
        if not self._rows:
            self.summary_label.setText("No save backups found.")
            self.btn_delete.setEnabled(False)
            self.btn_delete.setText("Delete Selected")
            return

        selected = self._selected_backups()
        total_size = sum(b.size for _, b in self._rows)
        selected_size = sum(b.size for b in selected)

        self.summary_label.setText(
            f"{len(self._rows)} backup(s), {format_size(total_size)} in total. "
            f"Selected: {len(selected)} ({format_size(selected_size)})."
        )
        self.btn_delete.setEnabled(bool(selected))
        self.btn_delete.setText(f"Delete Selected ({len(selected)})" if selected else "Delete Selected")

    # --- Actions ---

    def _delete_selected(self):
        selected = self._selected_backups()
        if not selected:
            return

        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Icon.Question)
        confirm.setWindowTitle("Delete Save Backups")
        confirm.setText(
            f"Delete {len(selected)} save backup(s) ({format_size(sum(b.size for b in selected))})?\n\n"
            "This action is undoable."
        )
        confirm.setDetailedText("\n".join(str(b.folder) for b in selected))
        confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm.setDefaultButton(QMessageBox.StandardButton.No)

        if confirm.exec() != QMessageBox.StandardButton.Yes:
            log.info("Deleting save backups cancelled.", silent=True)
            return

        deleted, failed = delete_fpaths([b.folder for b in selected])
        log.info(f"Deleted {len(deleted)} of {len(selected)} save backup(s).")

        # Remove playthrough folders that have no backups left
        for playthrough_dir in {b.folder.parent for b in selected}:
            try:
                if playthrough_dir.is_dir() and not any(playthrough_dir.iterdir()):
                    playthrough_dir.rmdir()
                    log.info(f"Removed empty playthrough folder: '{playthrough_dir}'", silent=True)
            except OSError as e:
                log.warning(f"Unable to remove empty playthrough folder '{playthrough_dir}': {e}")

        self.refresh()

        if failed:
            msgbox = QMessageBox(self)
            msgbox.setIcon(QMessageBox.Icon.Warning)
            msgbox.setWindowTitle("Some Backups Not Deleted")
            msgbox.setText(
                f"Deleted {len(deleted)} backup(s), but {len(failed)} could not be deleted:\n\n"
                + "\n".join(str(f) for f in failed)
            )
            msgbox.exec()

    def _show_backups_folder(self):
        folder = self.backups_dir if self.backups_dir.is_dir() else services().config.config_dir
        log.info(f"Opening save backups folder: '{folder}'", silent=True)
        open_in_file_manager(folder)
