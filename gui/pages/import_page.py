"""
听书工坊 (Audiobook Workshop) - Import page.

Provides drag-and-drop file selection for PDF/TXT/MD/EPUB books and
MinerU PDF conversion triggering.
"""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont
from PyQt6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    isDarkTheme,
)

from gui.i18n import t
from gui.styles import (
    DRAG_DROP_AREA_STYLE,
    DRAG_DROP_AREA_STYLE_DARK,
    FONT_SIZE_PAGE_TITLE,
    MARGIN_STANDARD,
    SPACING_LARGE,
    SPACING_MEDIUM,
    Colors,
    DarkColors,
)

# Accepted file extensions (lowercase, with dot)
_ACCEPTED_EXTENSIONS = {".pdf", ".txt", ".md", ".epub"}

# File dialog filter string
_FILE_FILTER = "书籍文件 (*.pdf *.txt *.md *.epub)"


def _format_file_size(size_bytes: int) -> str:
    """Return a human-readable file size string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _extension_to_type_label(ext: str) -> str:
    """Map a file extension to a display label."""
    mapping = {
        ".pdf": "PDF 文档",
        ".txt": "纯文本文件",
        ".md": "Markdown 文件",
        ".epub": "EPUB 电子书",
    }
    return mapping.get(ext.lower(), ext.upper())


class ImportPage(QWidget):
    """Import page: file selection via drag-drop or dialog, conversion."""

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------
    file_selected = pyqtSignal(str)          # absolute path of selected file
    convert_requested = pyqtSignal()         # user clicked "开始转换"
    content_ready = pyqtSignal(str, str)     # (content, book_name)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("importPage")
        self.setAcceptDrops(True)

        self._selected_path: str | None = None

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
        self._title_label = BodyLabel(t("import.title"), self)
        title_font = self._title_label.font()
        title_font.setPixelSize(FONT_SIZE_PAGE_TITLE)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        self._title_label.setObjectName("pageTitle")
        root_layout.addWidget(self._title_label)

        # --- File selection card ---
        self._file_card = CardWidget(self)
        file_card_layout = QVBoxLayout(self._file_card)
        file_card_layout.setContentsMargins(
            MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD,
        )
        file_card_layout.setSpacing(SPACING_MEDIUM)

        # Drag-drop area
        self._drag_area = QFrame(self._file_card)
        self._drag_area.setObjectName("dragDropArea")
        self._drag_area.setMinimumHeight(160)
        self._drag_area.setAcceptDrops(True)
        self._update_drag_area_style()

        drag_layout = QVBoxLayout(self._drag_area)
        drag_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drag_hint_label = BodyLabel(t("import.drag_hint"), self._drag_area)
        self._drag_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drag_layout.addWidget(self._drag_hint_label)

        file_card_layout.addWidget(self._drag_area)

        # "选择文件" button
        self._select_btn = PushButton(FluentIcon.FOLDER, t("import.select_file"), self._file_card)
        self._select_btn.clicked.connect(self._on_select_file_clicked)
        file_card_layout.addWidget(self._select_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # File info labels (hidden until a file is selected)
        self._info_widget = QWidget(self._file_card)
        info_layout = QVBoxLayout(self._info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(SPACING_MEDIUM)

        self._name_label = BodyLabel("", self._info_widget)
        self._size_label = BodyLabel("", self._info_widget)
        self._type_label = BodyLabel("", self._info_widget)
        info_layout.addWidget(self._name_label)
        info_layout.addWidget(self._size_label)
        info_layout.addWidget(self._type_label)
        self._info_widget.setVisible(False)

        file_card_layout.addWidget(self._info_widget)
        root_layout.addWidget(self._file_card)

        # --- Conversion card ---
        self._convert_card = CardWidget(self)
        convert_card_layout = QVBoxLayout(self._convert_card)
        convert_card_layout.setContentsMargins(
            MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD,
        )
        convert_card_layout.setSpacing(SPACING_MEDIUM)

        # "开始转换" button
        self._convert_btn = PrimaryPushButton(
            FluentIcon.PLAY, t("import.start_convert"), self._convert_card,
        )
        self._convert_btn.setEnabled(False)
        self._convert_btn.clicked.connect(self._on_convert_clicked)
        convert_card_layout.addWidget(self._convert_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Progress bar (hidden until conversion starts)
        self._progress_bar = ProgressBar(self._convert_card)
        self._progress_bar.setVisible(False)
        convert_card_layout.addWidget(self._progress_bar)

        # Status label
        self._status_label = BodyLabel("", self._convert_card)
        convert_card_layout.addWidget(self._status_label)

        root_layout.addWidget(self._convert_card)

        # Push remaining space to the bottom
        root_layout.addStretch(1)

    # ------------------------------------------------------------------
    # Drag and drop
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData() and event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    ext = Path(url.toLocalFile()).suffix.lower()
                    if ext in _ACCEPTED_EXTENSIONS:
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        if event.mimeData() and event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    ext = Path(path).suffix.lower()
                    if ext in _ACCEPTED_EXTENSIONS:
                        self._set_selected_file(path)
                        event.acceptProposedAction()
                        return
        event.ignore()

    # ------------------------------------------------------------------
    # File selection
    # ------------------------------------------------------------------
    def _on_select_file_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("import.select_file"), "", _FILE_FILTER,
        )
        if path:
            self._set_selected_file(path)

    def _set_selected_file(self, path: str) -> None:
        self._selected_path = path
        p = Path(path)

        # Update info labels
        self._name_label.setText(f"{t('import.file_name')}: {p.name}")
        self._size_label.setText(
            f"{t('import.file_size')}: {_format_file_size(p.stat().st_size)}",
        )
        self._type_label.setText(
            f"{t('import.file_type')}: {_extension_to_type_label(p.suffix)}",
        )
        self._info_widget.setVisible(True)

        # Enable conversion button
        self._convert_btn.setEnabled(True)
        self._status_label.setText("")

        # Emit signal
        self.file_selected.emit(path)

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------
    def _on_convert_clicked(self) -> None:
        if self._selected_path is None:
            InfoBar.warning(
                title=t("common.warning"),
                content=t("import.no_file"),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )
            return

        ext = Path(self._selected_path).suffix.lower()

        if ext == ".pdf":
            # PDF needs MinerU conversion -- MainWindow will create the worker
            self._status_label.setText(t("import.converting"))
            self._progress_bar.setVisible(True)
            self._progress_bar.setValue(0)
            self._convert_btn.setEnabled(False)
            self.convert_requested.emit()
        else:
            # TXT / MD / EPUB -- read directly
            self._status_label.setText(t("import.reading_file"))
            try:
                content = Path(self._selected_path).read_text(encoding="utf-8")
                book_name = Path(self._selected_path).stem
                self._status_label.setText(t("import.convert_success"))
                self.content_ready.emit(content, book_name)
            except Exception as exc:
                self._status_label.setText(f"{t('import.convert_error')}: {exc}")
                InfoBar.error(
                    title=t("common.error"),
                    content=str(exc),
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=5000,
                )

    # ------------------------------------------------------------------
    # Public helpers (called by MainWindow)
    # ------------------------------------------------------------------
    def get_selected_path(self) -> str | None:
        """Return the currently selected file path, or *None*."""
        return self._selected_path

    def set_progress(self, value: int, message: str = "") -> None:
        """Update the conversion progress bar (0-100)."""
        self._progress_bar.setValue(value)
        if message:
            self._status_label.setText(message)

    def set_status(self, text: str) -> None:
        """Update the status label text."""
        self._status_label.setText(text)

    def on_convert_finished(self, success: bool, message: str = "") -> None:
        """Called when MinerU conversion finishes."""
        self._progress_bar.setVisible(False)
        self._convert_btn.setEnabled(True)
        if success:
            self._status_label.setText(t("import.convert_success"))
        else:
            self._status_label.setText(f"{t('import.convert_error')}: {message}")

    # ------------------------------------------------------------------
    # Theme helpers
    # ------------------------------------------------------------------
    def _update_drag_area_style(self) -> None:
        style = DRAG_DROP_AREA_STYLE_DARK if isDarkTheme() else DRAG_DROP_AREA_STYLE
        self._drag_area.setStyleSheet(style)
