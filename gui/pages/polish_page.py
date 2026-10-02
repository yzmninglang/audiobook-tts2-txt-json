"""
听书工坊 (Audiobook Workshop) - Text polishing page.

Sits between chapter splitting and JSON generation.  Offers LLM provider /
concurrency controls, toggleable polish rules (tables, numbers, cleanup),
chapter selection, a side-by-side original-vs-polished preview, and
real-time progress / log output.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
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
    ComboBox,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    ListWidget,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    Slider,
    SpinBox,
    SubtitleLabel,
)

from gui.i18n import t
from gui.styles import SPACING_MEDIUM, SPACING_SMALL, MARGIN_STANDARD

_STATUS_ICONS = {
    "pending": "⏳",       # hourglass
    "processing": "\U0001f504",  # arrows
    "done": "✅",          # check mark
    "error": "❌",         # cross mark
}

_PROVIDERS = ["OpenRouter", "Gemini", "Qwen"]

# Polish rule ids (must match keys in gui.core.pipeline.POLISH_RULES)
_RULE_KEYS = ("tables", "numbers", "cleanup")


class PolishPage(QWidget):
    """Page for polishing chapter text into a listenable spoken script."""

    polish_requested = pyqtSignal(list, str, int, int, list)
    cancel_requested = pyqtSignal()
    export_requested = pyqtSignal(str)  # target directory
    next_step = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("polishPage")
        # Each row: {"index": int, "name": str, "original": str, "polished": str | None}
        self._rows: list[dict] = []
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

        title_label = BodyLabel(t("polish.title"), self)
        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        left_layout.addWidget(title_label)

        hint_label = BodyLabel(t("polish.hint"), self)
        hint_label.setWordWrap(True)
        left_layout.addWidget(hint_label)

        # --- Settings card ---
        settings_card = CardWidget(self)
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        settings_layout.setSpacing(SPACING_SMALL)

        provider_row = QHBoxLayout()
        provider_row.setSpacing(SPACING_SMALL)
        provider_row.addWidget(BodyLabel(t("gen.provider"), self))
        self.provider_combo = ComboBox(self)
        self.provider_combo.addItems(_PROVIDERS)
        provider_row.addWidget(self.provider_combo, 1)
        settings_layout.addLayout(provider_row)

        workers_row = QHBoxLayout()
        workers_row.setSpacing(SPACING_SMALL)
        workers_row.addWidget(BodyLabel(t("gen.workers"), self))
        self.workers_slider = Slider(Qt.Orientation.Horizontal, self)
        self.workers_slider.setRange(1, 20)
        self.workers_slider.setValue(5)
        self.workers_value_label = BodyLabel("5", self)
        self.workers_value_label.setFixedWidth(28)
        self.workers_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.workers_slider.valueChanged.connect(
            lambda v: self.workers_value_label.setText(str(v))
        )
        workers_row.addWidget(self.workers_slider, 1)
        workers_row.addWidget(self.workers_value_label)
        settings_layout.addLayout(workers_row)

        chunk_row = QHBoxLayout()
        chunk_row.setSpacing(SPACING_SMALL)
        chunk_row.addWidget(BodyLabel(t("gen.chunk_size"), self))
        self.chunk_spin = SpinBox(self)
        self.chunk_spin.setRange(2000, 15000)
        self.chunk_spin.setSingleStep(500)
        self.chunk_spin.setValue(8000)
        chunk_row.addWidget(self.chunk_spin, 1)
        chunk_row.addWidget(BodyLabel(" " + t("gen.chunk_size_suffix"), self))
        settings_layout.addLayout(chunk_row)

        left_layout.addWidget(settings_card)

        # --- Rules card ---
        rules_card = CardWidget(self)
        rules_layout = QVBoxLayout(rules_card)
        rules_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        rules_layout.setSpacing(SPACING_SMALL)
        rules_layout.addWidget(SubtitleLabel(t("polish.rules"), self))

        self._rule_boxes: dict[str, QCheckBox] = {}
        for key in _RULE_KEYS:
            box = QCheckBox(t(f"polish.rule_{key}"), self)
            box.setChecked(True)
            rules_layout.addWidget(box)
            self._rule_boxes[key] = box

        left_layout.addWidget(rules_card)

        # --- Chapter selection card ---
        chapter_card = CardWidget(self)
        chapter_layout = QVBoxLayout(chapter_card)
        chapter_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        chapter_layout.setSpacing(SPACING_SMALL)

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

        self.chapter_list = ListWidget(self)
        self.chapter_list.itemClicked.connect(self._on_chapter_clicked)
        chapter_layout.addWidget(self.chapter_list)

        left_layout.addWidget(chapter_card, 1)

        # --- Action buttons ---
        self.start_btn = PrimaryPushButton(
            FluentIcon.EDIT, t("polish.start"), self
        )
        self.start_btn.clicked.connect(self._on_start_clicked)
        left_layout.addWidget(self.start_btn)

        self.cancel_btn = PushButton(t("common.cancel"), self)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)
        left_layout.addWidget(self.cancel_btn)

        self.export_btn = PushButton(FluentIcon.SAVE, t("polish.export"), self)
        self.export_btn.clicked.connect(self._on_export_clicked)
        left_layout.addWidget(self.export_btn)

        self.next_btn = PrimaryPushButton(
            FluentIcon.CHEVRON_RIGHT, t("polish.next"), self
        )
        self.next_btn.clicked.connect(self.next_step.emit)
        left_layout.addWidget(self.next_btn)

        splitter.addWidget(left_panel)

        # --- Right panel ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(
            SPACING_MEDIUM, MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD
        )
        right_layout.setSpacing(SPACING_MEDIUM)

        right_split = QSplitter(Qt.Orientation.Vertical, self)

        # Preview card (original | polished)
        preview_card = CardWidget(self)
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        preview_layout.setSpacing(SPACING_SMALL)
        preview_layout.addWidget(SubtitleLabel(t("polish.preview"), self))

        preview_split = QSplitter(Qt.Orientation.Horizontal, self)

        original_wrap = QWidget()
        original_layout = QVBoxLayout(original_wrap)
        original_layout.setContentsMargins(0, 0, 0, 0)
        original_layout.setSpacing(SPACING_SMALL)
        original_layout.addWidget(BodyLabel(t("polish.original"), self))
        self.original_text = QPlainTextEdit(self)
        self.original_text.setReadOnly(True)
        self.original_text.setPlaceholderText(t("polish.no_preview"))
        original_layout.addWidget(self.original_text)
        preview_split.addWidget(original_wrap)

        polished_wrap = QWidget()
        polished_layout = QVBoxLayout(polished_wrap)
        polished_layout.setContentsMargins(0, 0, 0, 0)
        polished_layout.setSpacing(SPACING_SMALL)
        polished_layout.addWidget(BodyLabel(t("polish.polished"), self))
        self.polished_text = QPlainTextEdit(self)
        self.polished_text.setReadOnly(True)
        self.polished_text.setPlaceholderText(t("polish.no_preview"))
        polished_layout.addWidget(self.polished_text)
        preview_split.addWidget(polished_wrap)

        preview_split.setStretchFactor(0, 50)
        preview_split.setStretchFactor(1, 50)
        preview_layout.addWidget(preview_split, 1)

        right_split.addWidget(preview_card)

        # Progress card
        progress_card = CardWidget(self)
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        progress_layout.setSpacing(SPACING_SMALL)
        progress_layout.addWidget(SubtitleLabel(t("polish.progress"), self))

        self.status_list = ListWidget(self)
        progress_layout.addWidget(self.status_list, 1)

        self.progress_bar = ProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        right_split.addWidget(progress_card)

        # Log card
        log_card = CardWidget(self)
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        log_layout.setSpacing(SPACING_SMALL)
        log_layout.addWidget(SubtitleLabel(t("polish.log"), self))

        self.log_text = QPlainTextEdit(self)
        self.log_text.setReadOnly(True)
        mono = QFont("Consolas", 10)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.log_text.setFont(mono)
        log_layout.addWidget(self.log_text, 1)

        right_split.addWidget(log_card)

        right_split.setStretchFactor(0, 40)
        right_split.setStretchFactor(1, 25)
        right_split.setStretchFactor(2, 35)

        right_layout.addWidget(right_split, 1)

        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 40)
        splitter.setStretchFactor(1, 60)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update_chapters(self, rows: list[dict]) -> None:
        """Populate the chapter list.

        Parameters
        ----------
        rows : list[dict]
            Each dict has ``index`` (int), ``name`` (str) and
            ``original`` (str).  ``polished`` is filled in later.
        """
        self._rows = []
        for row in rows:
            self._rows.append({
                "index": row["index"],
                "name": row["name"],
                "original": row.get("original", ""),
                "polished": row.get("polished"),
            })

        self.chapter_list.clear()
        for row in self._rows:
            item = QListWidgetItem(row["name"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.chapter_list.addItem(item)

        self.original_text.clear()
        self.polished_text.clear()

    def has_polished(self) -> bool:
        """Return True if at least one chapter has polished text."""
        return any(row.get("polished") for row in self._rows)

    def set_polished(self, chapter_index: int, text: str) -> None:
        """Store and (if selected) display a chapter's polished text."""
        for i, row in enumerate(self._rows):
            if row["index"] == chapter_index:
                row["polished"] = text
                if self._is_selected(i):
                    self.polished_text.setPlainText(text)
                return

    def update_chapter_status(
        self, ch_index: int, status: str, message: str
    ) -> None:
        """Update a chapter's row in the progress list (matched by index)."""
        icon = _STATUS_ICONS.get(status, "")
        text = f"{icon} P{ch_index:02d} {message}"

        for i in range(self.status_list.count()):
            item = self.status_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == ch_index:
                item.setText(text)
                return

        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, ch_index)
        self.status_list.addItem(item)

    def append_log(self, message: str) -> None:
        self.log_text.appendPlainText(message)
        scrollbar = self.log_text.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def reset_progress(self) -> None:
        self.status_list.clear()
        self.progress_bar.setValue(0)
        self.log_text.clear()

    def set_polishing(self, active: bool) -> None:
        self.start_btn.setVisible(not active)
        self.cancel_btn.setVisible(active)
        self.provider_combo.setEnabled(not active)
        self.workers_slider.setEnabled(not active)
        self.chunk_spin.setEnabled(not active)
        self.select_all_btn.setEnabled(not active)
        self.deselect_all_btn.setEnabled(not active)
        self.export_btn.setEnabled(not active)
        self.next_btn.setEnabled(not active)
        for box in self._rule_boxes.values():
            box.setEnabled(not active)

    def clear(self) -> None:
        self._rows = []
        self.chapter_list.clear()
        self.original_text.clear()
        self.polished_text.clear()
        self.reset_progress()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _is_selected(self, row_index: int) -> bool:
        item = self.chapter_list.item(row_index)
        return (
            item is not None
            and item.checkState() == Qt.CheckState.Checked
        )

    def _select_all(self) -> None:
        for i in range(self.chapter_list.count()):
            item = self.chapter_list.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Checked)

    def _deselect_all(self) -> None:
        for i in range(self.chapter_list.count()):
            item = self.chapter_list.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

    def _get_selected_indices(self) -> list[int]:
        indices: list[int] = []
        for i in range(self.chapter_list.count()):
            item = self.chapter_list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                indices.append(i)
        return indices

    def _on_chapter_clicked(self, item: QListWidgetItem) -> None:
        idx = self.chapter_list.row(item)
        if not (0 <= idx < len(self._rows)):
            return
        row = self._rows[idx]
        self.original_text.setPlainText(row["original"])
        self.polished_text.setPlainText(row["polished"] or "")

    def _on_export_clicked(self) -> None:
        """Pick a folder and ask MainWindow to write the polished text there."""
        if not self.has_polished():
            InfoBar.warning(
                t("common.warning"),
                t("polish.no_polished"),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )
            return

        directory = QFileDialog.getExistingDirectory(self, t("polish.export"), "")
        if directory:
            self.export_requested.emit(directory)

    def _on_start_clicked(self) -> None:
        selected = self._get_selected_indices()
        provider = self.provider_combo.currentText()
        workers = self.workers_slider.value()
        chunk_size = self.chunk_spin.value()
        rules = [k for k, box in self._rule_boxes.items() if box.isChecked()]
        self.polish_requested.emit(selected, provider, workers, chunk_size, rules)
