"""
听书工坊 (Audiobook Workshop) - OCR preview and edit page.

Shows the markdown produced by MinerU, lets the user edit it,
save it as a .md file, browse history, and then continue to
the chapter-split stage.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
)

from gui.core.history import (
    HistoryEntry,
    delete_history,
    list_history,
    load_history_content,
)
from gui.i18n import t
from gui.styles import (
    FONT_SIZE_PAGE_TITLE,
    MARGIN_LARGE,
    MARGIN_STANDARD,
    SPACING_LARGE,
    SPACING_MEDIUM,
    SPACING_SMALL,
)


class HistoryDialog(QDialog):
    """Simple dialog listing available history entries."""

    entry_selected = pyqtSignal(str, str)  # (book_name, content)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("ocr_preview.history_title"))
        self.setMinimumSize(500, 400)
        self.resize(600, 500)

        self._entries: list[HistoryEntry] = []

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_MEDIUM)

        self._list = QListWidget(self)
        layout.addWidget(self._list, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(SPACING_SMALL)

        self._delete_btn = QPushButton(t("common.cancel"))
        self._delete_btn.setText("删除")
        self._delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(self._delete_btn)

        btn_row.addStretch()

        self._load_btn = QPushButton(t("common.confirm"))
        self._load_btn.clicked.connect(self._on_load)
        btn_row.addWidget(self._load_btn)

        layout.addLayout(btn_row)

        self._refresh()

    def _refresh(self) -> None:
        self._list.clear()
        self._entries = list_history()

        if not self._entries:
            item = QListWidgetItem(t("ocr_preview.no_history"))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._list.addItem(item)
            return

        for entry in self._entries:
            display = f"{entry.book_name}  ({entry.created_at})"
            if entry.source_type:
                display += f"  [{entry.source_type}]"
            self._list.addItem(display)

    def _on_load(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._entries):
            return
        entry = self._entries[row]
        content = load_history_content(entry.filepath)
        self.entry_selected.emit(entry.book_name, content)
        self.accept()

    def _on_delete(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._entries):
            return
        entry = self._entries[row]
        delete_history(entry.filepath)
        self._refresh()


class OcrPreviewPage(QWidget):
    """Editable markdown preview with history browser and save/continue actions."""

    save_md_requested = pyqtSignal(str)           # markdown content
    continue_to_split = pyqtSignal(str, str)       # (content, book_name)
    history_load_requested = pyqtSignal(str, str)  # (book_name, content)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ocrPreviewPage")
        self._book_name = ""
        self._init_ui()

    def _init_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(MARGIN_LARGE, MARGIN_LARGE, MARGIN_LARGE, MARGIN_LARGE)
        root.setSpacing(SPACING_LARGE)

        # Title
        title = BodyLabel(t("ocr_preview.title"))
        title_font = QFont()
        title_font.setPixelSize(FONT_SIZE_PAGE_TITLE)
        title_font.setBold(True)
        title.setFont(title_font)
        root.addWidget(title)

        # Editor
        from PyQt6.QtWidgets import QPlainTextEdit

        self._editor = QPlainTextEdit(self)
        mono = QFont("Consolas", 10)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._editor.setFont(mono)
        self._editor.setPlaceholderText("Markdown content ...")
        root.addWidget(self._editor, 1)

        # Bottom action card
        card = CardWidget(self)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(
            MARGIN_STANDARD, SPACING_MEDIUM, MARGIN_STANDARD, SPACING_MEDIUM
        )
        card_layout.setSpacing(SPACING_MEDIUM)

        self._history_btn = PushButton(FluentIcon.HISTORY, t("ocr_preview.load_history"), self)
        self._save_btn = PushButton(FluentIcon.SAVE, t("ocr_preview.save_md"), self)
        self._continue_btn = PrimaryPushButton(FluentIcon.ACCEPT, t("ocr_preview.continue_split"), self)

        self._history_btn.clicked.connect(self._on_history)
        self._save_btn.clicked.connect(self._on_save)
        self._continue_btn.clicked.connect(self._on_continue)

        card_layout.addWidget(self._history_btn)
        card_layout.addStretch()
        card_layout.addWidget(self._save_btn)
        card_layout.addWidget(self._continue_btn)

        root.addWidget(card)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_content(self, markdown: str, book_name: str = "") -> None:
        """Load markdown into the editor."""
        self._editor.setPlainText(markdown)
        if book_name:
            self._book_name = book_name

    def get_content(self) -> str:
        return self._editor.toPlainText()

    def clear(self) -> None:
        self._editor.clear()
        self._book_name = ""

    # ------------------------------------------------------------------
    # Private slots
    # ------------------------------------------------------------------

    def _on_history(self) -> None:
        dlg = HistoryDialog(self)
        dlg.entry_selected.connect(self._load_from_history)
        dlg.exec()

    def _load_from_history(self, book_name: str, content: str) -> None:
        self._book_name = book_name
        self._editor.setPlainText(content)
        self.history_load_requested.emit(book_name, content)

    def _on_save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            t("ocr_preview.save_md"),
            f"{self._book_name or 'output'}.md",
            "Markdown (*.md)",
        )
        if path:
            Path(path).write_text(self._editor.toPlainText(), encoding="utf-8")
            self.save_md_requested.emit(path)

    def _on_continue(self) -> None:
        content = self._editor.toPlainText()
        self.continue_to_split.emit(content, self._book_name)
