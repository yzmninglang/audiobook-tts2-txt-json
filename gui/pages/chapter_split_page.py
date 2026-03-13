"""
听书工坊 (Audiobook Workshop) - Chapter split page.

Left-right layout for editing a chapter title list, configuring a
similarity threshold, and previewing / selecting split results.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
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
    FluentIcon,
    ListWidget,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    Slider,
    SubtitleLabel,
    isDarkTheme,
)

from gui.i18n import t
from gui.styles import (
    FONT_SIZE_PAGE_TITLE,
    MARGIN_STANDARD,
    SPACING_LARGE,
    SPACING_MEDIUM,
    SPACING_SMALL,
)


class ChapterSplitPage(QWidget):
    """Chapter splitting page with left (edit) / right (preview) panels."""

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------
    split_requested = pyqtSignal(str, list, int)  # (content, titles, threshold)
    next_step = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("chapterSplitPage")

        self._markdown_content: str = ""
        # Stores split chapter data: list of (title, content) tuples
        self._chapters: list[tuple[str, str]] = []

        self._init_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(
            MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD,
        )
        root_layout.setSpacing(SPACING_LARGE)

        # --- Page title ---
        self._title_label = BodyLabel(t("split.title"), self)
        title_font = self._title_label.font()
        title_font.setPixelSize(FONT_SIZE_PAGE_TITLE)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        self._title_label.setObjectName("pageTitle")
        root_layout.addWidget(self._title_label)

        # --- Splitter with left / right panels ---
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)

        self._build_left_panel()
        self._build_right_panel()

        # 55% / 45% initial ratio
        self._splitter.setStretchFactor(0, 55)
        self._splitter.setStretchFactor(1, 45)

        root_layout.addWidget(self._splitter, stretch=1)

    # ------------------------------------------------------------------
    # Left panel
    # ------------------------------------------------------------------
    def _build_left_panel(self) -> None:
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, SPACING_MEDIUM, 0)
        left_layout.setSpacing(SPACING_MEDIUM)

        # Section title
        self._chapter_list_title = SubtitleLabel(t("split.chapter_list"), left_widget)
        left_layout.addWidget(self._chapter_list_title)

        # Chapter titles text editor
        self._chapter_edit = QPlainTextEdit(left_widget)
        self._chapter_edit.setPlaceholderText("每行一个章节标题...")
        left_layout.addWidget(self._chapter_edit, stretch=1)

        # "从文件加载" button
        self._load_btn = PushButton(
            FluentIcon.DOCUMENT, t("split.load_from_file"), left_widget,
        )
        self._load_btn.clicked.connect(self._on_load_from_file)
        left_layout.addWidget(self._load_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Threshold row: label + slider + value label
        threshold_row = QHBoxLayout()
        threshold_row.setSpacing(SPACING_SMALL)

        self._threshold_label = BodyLabel(t("split.threshold"), left_widget)
        threshold_row.addWidget(self._threshold_label)

        self._threshold_slider = Slider(Qt.Orientation.Horizontal, left_widget)
        self._threshold_slider.setRange(20, 100)
        self._threshold_slider.setValue(40)
        self._threshold_slider.valueChanged.connect(self._on_threshold_changed)
        threshold_row.addWidget(self._threshold_slider, stretch=1)

        self._threshold_value_label = BodyLabel("40%", left_widget)
        self._threshold_value_label.setFixedWidth(48)
        threshold_row.addWidget(self._threshold_value_label)

        left_layout.addLayout(threshold_row)

        # "分割章节" button
        self._split_btn = PrimaryPushButton(
            FluentIcon.CUT, t("split.start_split"), left_widget,
        )
        self._split_btn.clicked.connect(self._on_split_clicked)
        left_layout.addWidget(self._split_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Progress bar (hidden until splitting)
        self._progress_bar = ProgressBar(left_widget)
        self._progress_bar.setVisible(False)
        left_layout.addWidget(self._progress_bar)

        self._splitter.addWidget(left_widget)

    # ------------------------------------------------------------------
    # Right panel
    # ------------------------------------------------------------------
    def _build_right_panel(self) -> None:
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(SPACING_MEDIUM, 0, 0, 0)
        right_layout.setSpacing(SPACING_MEDIUM)

        # Content preview section
        self._preview_title = SubtitleLabel(t("split.content_preview"), right_widget)
        right_layout.addWidget(self._preview_title)

        self._preview_edit = QPlainTextEdit(right_widget)
        self._preview_edit.setReadOnly(True)
        self._preview_edit.setPlaceholderText(t("split.no_content"))
        right_layout.addWidget(self._preview_edit, stretch=1)

        # Split result section
        self._result_title = SubtitleLabel(t("split.split_result"), right_widget)
        right_layout.addWidget(self._result_title)

        self._chapter_list_widget = ListWidget(right_widget)
        self._chapter_list_widget.itemClicked.connect(self._on_chapter_item_clicked)
        right_layout.addWidget(self._chapter_list_widget, stretch=1)

        # "下一步" button
        self._next_btn = PrimaryPushButton(
            FluentIcon.ARROW_DOWN, t("split.next_step"), right_widget,
        )
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(self.next_step.emit)
        right_layout.addWidget(self._next_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._splitter.addWidget(right_widget)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_load_from_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("split.load_from_file"), "", "文本文件 (*.txt)",
        )
        if path:
            try:
                text = Path(path).read_text(encoding="utf-8")
                self._chapter_edit.setPlainText(text)
            except Exception:
                pass

    def _on_threshold_changed(self, value: int) -> None:
        self._threshold_value_label.setText(f"{value}%")

    def _on_split_clicked(self) -> None:
        titles_text = self._chapter_edit.toPlainText().strip()
        titles = [line.strip() for line in titles_text.splitlines() if line.strip()]
        threshold = self._threshold_slider.value()
        self.split_requested.emit(self._markdown_content, titles, threshold)

    def _on_chapter_item_clicked(self, item: QListWidgetItem) -> None:
        idx = self._chapter_list_widget.row(item)
        if 0 <= idx < len(self._chapters):
            _title, content = self._chapters[idx]
            self._preview_edit.setPlainText(content)

    # ------------------------------------------------------------------
    # Public helpers (called by MainWindow)
    # ------------------------------------------------------------------
    def update_content(self, text: str) -> None:
        """Set the markdown content to be split."""
        self._markdown_content = text
        self._preview_edit.setPlainText(text)

    def set_progress(self, value: int, message: str = "") -> None:
        """Update the splitting progress bar (0-100)."""
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(value)

    def set_chapters(self, chapters: list[tuple[str, str]]) -> None:
        """Populate the split result list.

        Parameters
        ----------
        chapters : list of (title, content) tuples
        """
        self._chapters = chapters
        self._chapter_list_widget.clear()

        for idx, (title, _content) in enumerate(chapters, start=1):
            item = QListWidgetItem(f"{idx}. {title}")
            self._chapter_list_widget.addItem(item)

        self._progress_bar.setVisible(False)
        self._next_btn.setEnabled(bool(chapters))

    def get_threshold(self) -> int:
        """Return the current similarity threshold value."""
        return self._threshold_slider.value()

    def get_chapter_titles(self) -> list[str]:
        """Return the list of chapter titles from the editor."""
        text = self._chapter_edit.toPlainText().strip()
        return [line.strip() for line in text.splitlines() if line.strip()]
