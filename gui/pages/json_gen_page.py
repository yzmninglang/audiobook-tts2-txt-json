"""
听书工坊 (Audiobook Workshop) - JSON generation page.

Provides LLM provider selection, parallel processing controls,
chapter selection with checkboxes, and real-time progress / log output.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ComboBox,
    FluentIcon,
    ListWidget,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    Slider,
    SpinBox,
    SubtitleLabel,
    isDarkTheme,
)

from gui.i18n import t
from gui.styles import SPACING_LARGE, SPACING_MEDIUM, SPACING_SMALL, MARGIN_STANDARD

# Status icon prefixes
_STATUS_ICONS = {
    "pending": "\u23f3",      # hourglass
    "processing": "\U0001f504",  # arrows
    "done": "\u2705",         # check mark
    "error": "\u274c",        # cross mark
}

_PROVIDERS = ["OpenRouter", "Gemini", "Qwen"]


class JsonGenPage(QWidget):
    """Page for generating JSON from chapters using an LLM provider."""

    generate_requested = pyqtSignal(list, str, int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("jsonGenPage")
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
        title_label = BodyLabel(t("gen.title"), self)
        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        left_layout.addWidget(title_label)

        # --- Settings card ---
        settings_card = CardWidget(self)
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        settings_layout.setSpacing(SPACING_SMALL)

        # Provider row
        provider_row = QHBoxLayout()
        provider_row.setSpacing(SPACING_SMALL)
        provider_label = BodyLabel(t("gen.provider"), self)
        self.provider_combo = ComboBox(self)
        self.provider_combo.addItems(_PROVIDERS)
        provider_row.addWidget(provider_label)
        provider_row.addWidget(self.provider_combo, 1)
        settings_layout.addLayout(provider_row)

        # Workers row
        workers_row = QHBoxLayout()
        workers_row.setSpacing(SPACING_SMALL)
        workers_label = BodyLabel(t("gen.workers"), self)
        self.workers_slider = Slider(Qt.Orientation.Horizontal, self)
        self.workers_slider.setRange(1, 20)
        self.workers_slider.setValue(5)
        self.workers_value_label = BodyLabel("5", self)
        self.workers_value_label.setFixedWidth(28)
        self.workers_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.workers_slider.valueChanged.connect(
            lambda v: self.workers_value_label.setText(str(v))
        )
        workers_row.addWidget(workers_label)
        workers_row.addWidget(self.workers_slider, 1)
        workers_row.addWidget(self.workers_value_label)
        settings_layout.addLayout(workers_row)

        # Chunk size row
        chunk_row = QHBoxLayout()
        chunk_row.setSpacing(SPACING_SMALL)
        chunk_label = BodyLabel(t("gen.chunk_size"), self)
        self.chunk_spin = SpinBox(self)
        self.chunk_spin.setRange(2000, 15000)
        self.chunk_spin.setSingleStep(500)
        self.chunk_spin.setValue(8000)
        chunk_suffix = BodyLabel(" " + t("gen.chunk_size_suffix"), self)
        chunk_row.addWidget(chunk_label)
        chunk_row.addWidget(self.chunk_spin, 1)
        chunk_row.addWidget(chunk_suffix)
        settings_layout.addLayout(chunk_row)

        left_layout.addWidget(settings_card)

        # --- Chapter selection card ---
        chapter_card = CardWidget(self)
        chapter_layout = QVBoxLayout(chapter_card)
        chapter_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        chapter_layout.setSpacing(SPACING_SMALL)

        # Select-all / deselect-all buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(SPACING_SMALL)
        self.select_all_btn = PushButton(t("gen.select_all"), self)
        self.deselect_all_btn = PushButton(t("gen.deselect_all"), self)
        self.select_all_btn.clicked.connect(self._select_all)
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        btn_row.addWidget(self.select_all_btn)
        btn_row.addWidget(self.deselect_all_btn)
        btn_row.addStretch()
        chapter_layout.addLayout(btn_row)

        # Chapter list
        self.chapter_list = ListWidget(self)
        chapter_layout.addWidget(self.chapter_list)

        left_layout.addWidget(chapter_card, 1)

        # --- Action buttons ---
        self.generate_btn = PrimaryPushButton(t("gen.start_gen"), self)
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        left_layout.addWidget(self.generate_btn)

        self.cancel_btn = PushButton(t("common.cancel"), self)
        self.cancel_btn.setVisible(False)
        left_layout.addWidget(self.cancel_btn)

        splitter.addWidget(left_panel)

        # --- Right panel ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(
            SPACING_MEDIUM, MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD
        )
        right_layout.setSpacing(SPACING_MEDIUM)

        # --- Progress card ---
        progress_card = CardWidget(self)
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        progress_layout.setSpacing(SPACING_SMALL)

        progress_title = SubtitleLabel(t("gen.progress"), self)
        progress_layout.addWidget(progress_title)

        self.status_list = ListWidget(self)
        progress_layout.addWidget(self.status_list, 1)

        self.progress_bar = ProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        right_layout.addWidget(progress_card, 1)

        # --- Log card ---
        log_card = CardWidget(self)
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        log_layout.setSpacing(SPACING_SMALL)

        log_title = SubtitleLabel(t("gen.log"), self)
        log_layout.addWidget(log_title)

        self.log_text = QPlainTextEdit(self)
        self.log_text.setReadOnly(True)
        mono_font = QFont("Consolas", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.log_text.setFont(mono_font)
        log_layout.addWidget(self.log_text, 1)

        right_layout.addWidget(log_card, 1)

        splitter.addWidget(right_panel)

        # Splitter proportions: 45% left, 55% right
        splitter.setStretchFactor(0, 45)
        splitter.setStretchFactor(1, 55)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update_chapters(self, chapters: list[str]) -> None:
        """Populate the chapter list with checkboxes.

        Parameters
        ----------
        chapters : list[str]
            Display names for each chapter.
        """
        self.chapter_list.clear()
        for name in chapters:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.chapter_list.addItem(item)

    def select_all(self) -> None:
        """Check all chapter checkboxes."""
        self._select_all()

    def deselect_all(self) -> None:
        """Uncheck all chapter checkboxes."""
        self._deselect_all()

    def update_chapter_status(
        self, index: int, status: str, message: str
    ) -> None:
        """Update the status of a chapter in the progress list.

        Parameters
        ----------
        index : int
            Zero-based chapter index.
        status : str
            One of ``"pending"``, ``"processing"``, ``"done"``, ``"error"``.
        message : str
            Short description to display alongside the icon.
        """
        icon = _STATUS_ICONS.get(status, "")
        text = f"{icon} [{index + 1}] {message}"

        # Grow the status list if needed
        while self.status_list.count() <= index:
            self.status_list.addItem("")

        item = self.status_list.item(index)
        if item is not None:
            item.setText(text)

    def append_log(self, message: str) -> None:
        """Append a message to the log area and scroll to the bottom."""
        self.log_text.appendPlainText(message)
        scrollbar = self.log_text.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(scrollbar.maximum())

    def reset_progress(self) -> None:
        """Clear the progress list, progress bar, and log area."""
        self.status_list.clear()
        self.progress_bar.setValue(0)
        self.log_text.clear()

    def set_generating(self, generating: bool) -> None:
        """Toggle between generating and idle UI state."""
        self.generate_btn.setVisible(not generating)
        self.cancel_btn.setVisible(generating)
        self.provider_combo.setEnabled(not generating)
        self.workers_slider.setEnabled(not generating)
        self.chunk_spin.setEnabled(not generating)
        self.select_all_btn.setEnabled(not generating)
        self.deselect_all_btn.setEnabled(not generating)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _select_all(self) -> None:
        for i in range(self.chapter_list.count()):
            item = self.chapter_list.item(i)
            if item is not None:
                item.setCheckState(Qt.CheckState.Checked)

    def _deselect_all(self) -> None:
        for i in range(self.chapter_list.count()):
            item = self.chapter_list.item(i)
            if item is not None:
                item.setCheckState(Qt.CheckState.Unchecked)

    def _get_selected_indices(self) -> list[int]:
        indices: list[int] = []
        for i in range(self.chapter_list.count()):
            item = self.chapter_list.item(i)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                indices.append(i)
        return indices

    def _on_generate_clicked(self) -> None:
        selected = self._get_selected_indices()
        provider = self.provider_combo.currentText()
        workers = self.workers_slider.value()
        chunk_size = self.chunk_spin.value()
        self.generate_requested.emit(selected, provider, workers, chunk_size)
