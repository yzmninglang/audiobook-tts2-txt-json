"""
听书工坊 (Audiobook Workshop) - Speaker management page.

Provides speaker extraction, AI-based classification into voice
categories, a table editor for manual adjustments, JSON preview,
and export functionality.
"""

from __future__ import annotations

import json

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ComboBox,
    FluentIcon,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    isDarkTheme,
)

from gui.i18n import t
from gui.styles import SPACING_LARGE, SPACING_MEDIUM, SPACING_SMALL, MARGIN_STANDARD

_CATEGORY_OPTIONS = ["", "\u5c11\u7537", "\u5c11\u5973", "\u4e2d\u7537", "\u4e2d\u5973", "\u8001\u7537", "\u8001\u5973"]
_NARRATOR_NAME = "\u65c1\u767d"
_NARRATOR_CLASSIFICATION = "\u65c1\u767d"


class SpeakerPage(QWidget):
    """Page for managing speaker extraction, classification, and export."""

    extract_requested = pyqtSignal()
    classify_requested = pyqtSignal()
    apply_requested = pyqtSignal(dict)
    export_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("speakerPage")
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
        title_label = BodyLabel(t("speaker.title"), self)
        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        left_layout.addWidget(title_label)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(SPACING_SMALL)
        self.extract_btn = PushButton(t("speaker.extract"), self)
        self.classify_btn = PrimaryPushButton(t("speaker.ai_classify"), self)
        self.extract_btn.clicked.connect(self._on_extract_clicked)
        self.classify_btn.clicked.connect(self._on_classify_clicked)
        btn_row.addWidget(self.extract_btn)
        btn_row.addWidget(self.classify_btn)
        btn_row.addStretch()
        left_layout.addLayout(btn_row)

        # --- Speaker table card ---
        table_card = CardWidget(self)
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        table_layout.setSpacing(SPACING_SMALL)

        self.speaker_table = QTableWidget(0, 3, self)
        self.speaker_table.setHorizontalHeaderLabels([
            t("speaker.name"),
            t("speaker.count"),
            t("speaker.classification"),
        ])
        header = self.speaker_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.speaker_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.speaker_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        table_layout.addWidget(self.speaker_table)

        left_layout.addWidget(table_card, 1)

        splitter.addWidget(left_panel)

        # --- Right panel ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(
            SPACING_MEDIUM, MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD
        )
        right_layout.setSpacing(SPACING_MEDIUM)

        # --- Preview card ---
        preview_card = CardWidget(self)
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(
            SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM, SPACING_MEDIUM
        )
        preview_layout.setSpacing(SPACING_SMALL)

        preview_title = SubtitleLabel(t("speaker.preview"), self)
        preview_layout.addWidget(preview_title)

        self.preview_text = QPlainTextEdit(self)
        self.preview_text.setReadOnly(True)
        mono_font = QFont("Consolas", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.preview_text.setFont(mono_font)
        preview_layout.addWidget(self.preview_text, 1)

        right_layout.addWidget(preview_card, 1)

        # --- Bottom action buttons ---
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(SPACING_SMALL)
        self.apply_btn = PrimaryPushButton(t("speaker.apply"), self)
        self.export_btn = PushButton(t("speaker.export"), self)
        self.apply_btn.clicked.connect(self._on_apply_clicked)
        self.export_btn.clicked.connect(self._on_export_clicked)
        bottom_row.addStretch()
        bottom_row.addWidget(self.apply_btn)
        bottom_row.addWidget(self.export_btn)
        right_layout.addLayout(bottom_row)

        splitter.addWidget(right_panel)

        # Splitter proportions: 50% / 50%
        splitter.setStretchFactor(0, 50)
        splitter.setStretchFactor(1, 50)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update_speakers(self, speakers_list: list[tuple[str, int]]) -> None:
        """Populate the speaker table.

        Parameters
        ----------
        speakers_list : list[tuple[str, int]]
            Each tuple is ``(name, count)``.
        """
        self.speaker_table.setRowCount(0)
        self.speaker_table.setRowCount(len(speakers_list))

        for row, (name, count) in enumerate(speakers_list):
            # Name column
            name_item = QTableWidgetItem(name)
            name_item.setFlags(
                name_item.flags() & ~Qt.ItemFlag.ItemIsEditable
            )
            self.speaker_table.setItem(row, 0, name_item)

            # Count column
            count_item = QTableWidgetItem(str(count))
            count_item.setFlags(
                count_item.flags() & ~Qt.ItemFlag.ItemIsEditable
            )
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.speaker_table.setItem(row, 1, count_item)

            # Classification column
            if name == _NARRATOR_NAME:
                cls_item = QTableWidgetItem(_NARRATOR_CLASSIFICATION)
                cls_item.setFlags(
                    cls_item.flags() & ~Qt.ItemFlag.ItemIsEditable
                )
                cls_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.speaker_table.setItem(row, 2, cls_item)
            else:
                combo = QComboBox(self)
                combo.addItems(_CATEGORY_OPTIONS)
                self.speaker_table.setCellWidget(row, 2, combo)

    def set_classifications(
        self, classifications_dict: dict[str, list[str]]
    ) -> None:
        """Fill classification ComboBoxes from a mapping.

        Parameters
        ----------
        classifications_dict : dict[str, list[str]]
            Maps category name (e.g. ``"\u5c11\u7537"``) to a list of speaker names.
        """
        # Build reverse lookup: speaker_name -> category
        name_to_cat: dict[str, str] = {}
        for category, names in classifications_dict.items():
            for name in names:
                name_to_cat[name] = category

        for row in range(self.speaker_table.rowCount()):
            name_item = self.speaker_table.item(row, 0)
            if name_item is None:
                continue
            speaker_name = name_item.text()
            if speaker_name == _NARRATOR_NAME:
                continue

            combo = self.speaker_table.cellWidget(row, 2)
            if not isinstance(combo, QComboBox):
                continue

            category = name_to_cat.get(speaker_name, "")
            idx = combo.findText(category)
            if idx >= 0:
                combo.setCurrentIndex(idx)

    def get_classifications(self) -> dict[str, list[str]]:
        """Read ComboBoxes and build a ``{category: [names]}`` dict.

        Returns
        -------
        dict[str, list[str]]
            Only categories with at least one speaker are included.
        """
        result: dict[str, list[str]] = {}

        for row in range(self.speaker_table.rowCount()):
            name_item = self.speaker_table.item(row, 0)
            if name_item is None:
                continue
            speaker_name = name_item.text()

            if speaker_name == _NARRATOR_NAME:
                result.setdefault(_NARRATOR_CLASSIFICATION, []).append(
                    speaker_name
                )
                continue

            combo = self.speaker_table.cellWidget(row, 2)
            if not isinstance(combo, QComboBox):
                continue

            category = combo.currentText()
            if category:
                result.setdefault(category, []).append(speaker_name)

        return result

    def update_preview(self, chapter_results: list) -> None:
        """Show the first chapter's JSON in the preview pane.

        Parameters
        ----------
        chapter_results : list
            A list of chapter result objects (or dicts). The first
            item is serialised and displayed.
        """
        if not chapter_results:
            self.preview_text.setPlainText(t("speaker.no_results"))
            return

        first = chapter_results[0]
        # Support both Pydantic models and plain dicts
        if hasattr(first, "model_dump"):
            data = first.model_dump()
        elif hasattr(first, "dict"):
            data = first.dict()
        else:
            data = first

        formatted = json.dumps(data, ensure_ascii=False, indent=2)
        self.preview_text.setPlainText(formatted)

    def clear(self) -> None:
        """Reset the table and preview."""
        self.speaker_table.setRowCount(0)
        self.preview_text.clear()

    # ------------------------------------------------------------------
    # Private slots
    # ------------------------------------------------------------------
    def _on_extract_clicked(self) -> None:
        self.extract_requested.emit()

    def _on_classify_clicked(self) -> None:
        self.classify_requested.emit()

    def _on_apply_clicked(self) -> None:
        classifications = self.get_classifications()
        self.apply_requested.emit(classifications)

    def _on_export_clicked(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            t("speaker.export"),
            "",
        )
        if directory:
            self.export_requested.emit(directory)
