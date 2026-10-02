"""
听书工坊 (Audiobook Workshop) - TTS synthesis page.

Provides chapter selection, output directory choice, progress tracking,
and log output for the TTS synthesis pipeline.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QListWidgetItem,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon,
    LineEdit,
    ListWidget,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    SubtitleLabel,
    isDarkTheme,
)

from gui.i18n import t
from gui.styles import SPACING_LARGE, SPACING_MEDIUM, SPACING_SMALL, MARGIN_STANDARD

# Status icon prefixes
_STATUS_ICONS = {
    "pending": "\u23f3",
    "processing": "\U0001f504",
    "done": "\u2705",
    "error": "\u274c",
}


class TTSPage(QWidget):
    """Page for TTS synthesis of chapter JSON entries."""

    synthesize_requested = pyqtSignal(list, str)  # (selected_indices, output_dir)
    cancel_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ttsPage")
        self._init_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        root_layout.addWidget(splitter)

        # --- Left panel ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(
            MARGIN_STANDARD, MARGIN_STANDARD, SPACING_MEDIUM, MARGIN_STANDARD
        )
        left_layout.setSpacing(SPACING_MEDIUM)

        # Title
        title_label = BodyLabel(t("tts.title"), self)
        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        left_layout.addWidget(title_label)

        # --- Output dir card ---
        dir_card = CardWidget(self)
        dir_layout = QVBoxLayout(dir_card)
        dir_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        dir_layout.setSpacing(SPACING_SMALL)

        dir_row = QHBoxLayout()
        dir_row.setSpacing(SPACING_SMALL)
        dir_label = BodyLabel(t("tts.output_dir"), self)
        self._dir_edit = LineEdit(self)
        self._dir_edit.setReadOnly(True)
        self._dir_edit.setPlaceholderText(t("tts.select_dir"))
        self._dir_btn = PushButton(FluentIcon.FOLDER, t("tts.select_dir"), self)
        self._dir_btn.clicked.connect(self._on_select_dir)
        dir_row.addWidget(dir_label)
        dir_row.addWidget(self._dir_edit, 1)
        dir_row.addWidget(self._dir_btn)
        dir_layout.addLayout(dir_row)

        left_layout.addWidget(dir_card)

        # --- Chapter selection card ---
        chapter_card = CardWidget(self)
        chapter_layout = QVBoxLayout(chapter_card)
        chapter_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        chapter_layout.setSpacing(SPACING_SMALL)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(SPACING_SMALL)
        self._select_all_btn = PushButton(t("tts.select_all"), self)
        self._deselect_all_btn = PushButton(t("tts.deselect_all"), self)
        self._select_all_btn.clicked.connect(self._select_all)
        self._deselect_all_btn.clicked.connect(self._deselect_all)
        btn_row.addWidget(self._select_all_btn)
        btn_row.addWidget(self._deselect_all_btn)
        btn_row.addStretch()
        chapter_layout.addLayout(btn_row)

        self._chapter_list = ListWidget(self)
        chapter_layout.addWidget(self._chapter_list)

        left_layout.addWidget(chapter_card, 1)

        # --- Action buttons ---
        self._start_btn = PrimaryPushButton(FluentIcon.MEGAPHONE, t("tts.start"), self)
        self._start_btn.clicked.connect(self._on_start_clicked)
        left_layout.addWidget(self._start_btn)

        self._cancel_btn = PushButton(t("tts.cancel"), self)
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        left_layout.addWidget(self._cancel_btn)

        splitter.addWidget(left_panel)

        # --- Right panel ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(
            SPACING_MEDIUM, MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD
        )
        right_layout.setSpacing(SPACING_MEDIUM)

        # --- Chapter status card ---
        status_card = CardWidget(self)
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        status_layout.setSpacing(SPACING_SMALL)

        status_title = SubtitleLabel(t("tts.chapter_status"), self)
        status_layout.addWidget(status_title)

        self._status_list = ListWidget(self)
        status_layout.addWidget(self._status_list, 1)

        self._progress_bar = ProgressBar(self)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        status_layout.addWidget(self._progress_bar)

        right_layout.addWidget(status_card, 1)

        # --- Log card ---
        log_card = CardWidget(self)
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        log_layout.setSpacing(SPACING_SMALL)

        log_title = SubtitleLabel(t("tts.log"), self)
        log_layout.addWidget(log_title)

        self._log_text = QPlainTextEdit(self)
        self._log_text.setReadOnly(True)
        mono = QFont("Consolas", 10)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._log_text.setFont(mono)
        log_layout.addWidget(self._log_text, 1)

        right_layout.addWidget(log_card, 1)

        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 40)
        splitter.setStretchFactor(1, 60)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_chapters(self, chapter_names: list[str]) -> None:
        """Populate chapter list with checkboxes."""
        self._chapter_list.clear()
        for name in chapter_names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self._chapter_list.addItem(item)

    def set_output_dir(self, path: str) -> None:
        self._dir_edit.setText(path)

    def update_chapter_status(self, ch_index: int, status: str, message: str) -> None:
        """Update status display for a chapter (matched by chapter_index)."""
        icon = _STATUS_ICONS.get(status, "")
        text = f"{icon} P{ch_index:02d} {message}"

        # Find existing row by chapter index, or append
        for i in range(self._status_list.count()):
            item = self._status_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == ch_index:
                item.setText(text)
                return

        # Append new
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, ch_index)
        self._status_list.addItem(item)

    def update_entry_progress(self, ch_index: int, current: int, total: int) -> None:
        """Update the progress bar based on entry-level progress."""
        if total > 0:
            pct = int(current / total * 100)
            self._progress_bar.setValue(pct)

    def append_log(self, message: str) -> None:
        self._log_text.appendPlainText(message)
        scrollbar = self._log_text.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def reset_progress(self) -> None:
        self._status_list.clear()
        self._progress_bar.setValue(0)
        self._log_text.clear()

    def set_synthesizing(self, active: bool) -> None:
        self._start_btn.setVisible(not active)
        self._cancel_btn.setVisible(active)
        self._select_all_btn.setEnabled(not active)
        self._deselect_all_btn.setEnabled(not active)
        self._dir_btn.setEnabled(not active)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _select_all(self) -> None:
        for i in range(self._chapter_list.count()):
            item = self._chapter_list.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Checked)

    def _deselect_all(self) -> None:
        for i in range(self._chapter_list.count()):
            item = self._chapter_list.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

    def _get_selected_indices(self) -> list[int]:
        indices: list[int] = []
        for i in range(self._chapter_list.count()):
            item = self._chapter_list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                indices.append(i)
        return indices

    def _on_select_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, t("tts.select_dir"))
        if directory:
            self._dir_edit.setText(directory)

    def _on_start_clicked(self) -> None:
        selected = self._get_selected_indices()
        output_dir = self._dir_edit.text().strip()
        self.synthesize_requested.emit(selected, output_dir)

    def _on_cancel_clicked(self) -> None:
        self.cancel_requested.emit()
