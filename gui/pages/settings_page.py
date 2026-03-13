"""
听书工坊 (Audiobook Workshop) - Settings page.

Grouped settings displayed inside a scrollable area using CardWidget
containers.  Each card holds a form-like layout of label + input rows.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ComboBox,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PasswordLineEdit,
    PrimaryPushButton,
    ScrollArea,
    Slider,
    SpinBox,
    SubtitleLabel,
    isDarkTheme,
)

from gui.core.config import AppConfig
from gui.i18n import t
from gui.styles import (
    FONT_SIZE_PAGE_TITLE,
    MARGIN_LARGE,
    MARGIN_STANDARD,
    SPACING_LARGE,
    SPACING_MEDIUM,
    SPACING_SMALL,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_LABEL_WIDTH = 120


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_row(label_text: str, widget: QWidget) -> QHBoxLayout:
    """Create a horizontal row: fixed-width label on the left, widget on the right."""
    row = QHBoxLayout()
    row.setSpacing(SPACING_MEDIUM)

    label = BodyLabel(label_text)
    label.setFixedWidth(_LABEL_WIDTH)
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    row.addWidget(label)
    row.addWidget(widget, stretch=1)
    return row


def _make_group(title: str, rows: list[QHBoxLayout]) -> tuple[SubtitleLabel, CardWidget]:
    """Build a titled card group containing the given rows.

    Returns the subtitle label and the card widget so they can be added to
    the parent layout separately (subtitle sits *above* the card).
    """
    subtitle = SubtitleLabel(title)

    card = CardWidget()
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(
        MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD, MARGIN_STANDARD,
    )
    card_layout.setSpacing(SPACING_MEDIUM)

    for row in rows:
        card_layout.addLayout(row)

    return subtitle, card


# ---------------------------------------------------------------------------
# SettingsPage
# ---------------------------------------------------------------------------

class SettingsPage(ScrollArea):
    """Application settings page displayed as a scrollable form."""

    save_requested = pyqtSignal(object)  # emits AppConfig

    # -----------------------------------------------------------------
    # Construction
    # -----------------------------------------------------------------

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsPage")
        self.setWidgetResizable(True)

        scroll_widget = QWidget()
        scroll_widget.setObjectName("scrollWidget")
        self.setWidget(scroll_widget)

        root_layout = QVBoxLayout(scroll_widget)
        root_layout.setContentsMargins(MARGIN_LARGE, MARGIN_LARGE, MARGIN_LARGE, MARGIN_LARGE)
        root_layout.setSpacing(SPACING_LARGE)

        # --- Page title ---------------------------------------------------
        title_label = BodyLabel(t("settings.title"))
        title_font = QFont()
        title_font.setPixelSize(FONT_SIZE_PAGE_TITLE)
        title_font.setBold(True)
        title_label.setFont(title_font)
        root_layout.addWidget(title_label)

        # --- OpenRouter group --------------------------------------------
        self._openrouter_key = PasswordLineEdit()
        self._openrouter_key.setPlaceholderText(t("settings.api_key"))

        self._openrouter_url = LineEdit()
        self._openrouter_url.setPlaceholderText(t("settings.base_url"))

        self._openrouter_model = LineEdit()
        self._openrouter_model.setPlaceholderText(t("settings.model"))

        sub, card = _make_group(
            "OpenRouter 配置",
            [
                _make_row(t("settings.api_key"), self._openrouter_key),
                _make_row(t("settings.base_url"), self._openrouter_url),
                _make_row(t("settings.model"), self._openrouter_model),
            ],
        )
        root_layout.addWidget(sub)
        root_layout.addWidget(card)

        # --- Gemini group ------------------------------------------------
        self._gemini_key = PasswordLineEdit()
        self._gemini_key.setPlaceholderText(t("settings.api_key"))

        self._gemini_url = LineEdit()
        self._gemini_url.setPlaceholderText(t("settings.base_url"))

        sub, card = _make_group(
            "Gemini 配置",
            [
                _make_row(t("settings.api_key"), self._gemini_key),
                _make_row(t("settings.base_url"), self._gemini_url),
            ],
        )
        root_layout.addWidget(sub)
        root_layout.addWidget(card)

        # --- Qwen group --------------------------------------------------
        self._qwen_key = PasswordLineEdit()
        self._qwen_key.setPlaceholderText(t("settings.api_key"))

        self._qwen_url = LineEdit()
        self._qwen_url.setPlaceholderText(t("settings.base_url"))

        self._qwen_model = LineEdit()
        self._qwen_model.setPlaceholderText(t("settings.model"))

        sub, card = _make_group(
            "Qwen 配置",
            [
                _make_row(t("settings.api_key"), self._qwen_key),
                _make_row(t("settings.base_url"), self._qwen_url),
                _make_row(t("settings.model"), self._qwen_model),
            ],
        )
        root_layout.addWidget(sub)
        root_layout.addWidget(card)

        # --- MinerU group ------------------------------------------------
        self._mineru_token = PasswordLineEdit()
        self._mineru_token.setPlaceholderText(t("settings.api_token"))

        sub, card = _make_group(
            "MinerU 配置",
            [
                _make_row(t("settings.api_token"), self._mineru_token),
            ],
        )
        root_layout.addWidget(sub)
        root_layout.addWidget(card)

        # --- General group -----------------------------------------------
        # Theme combo
        self._theme_combo = ComboBox()
        self._theme_combo.addItems([
            t("settings.theme_light"),
            t("settings.theme_dark"),
            t("settings.theme_auto"),
        ])

        # Chunk size spin box
        self._chunk_spin = SpinBox()
        self._chunk_spin.setRange(2000, 15000)
        self._chunk_spin.setSingleStep(500)

        # Max workers spin box
        self._workers_spin = SpinBox()
        self._workers_spin.setRange(1, 20)

        # Similarity threshold slider + value label
        self._threshold_slider = Slider(Qt.Orientation.Horizontal)
        self._threshold_slider.setRange(20, 100)
        self._threshold_slider.setTickInterval(5)
        self._threshold_label = BodyLabel("40")
        self._threshold_label.setFixedWidth(32)
        self._threshold_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._threshold_slider.valueChanged.connect(
            lambda v: self._threshold_label.setText(str(v)),
        )

        # Wrap slider + value label in a single container widget so
        # _make_row receives one widget.
        slider_container = QWidget()
        slider_layout = QHBoxLayout(slider_container)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(SPACING_SMALL)
        slider_layout.addWidget(self._threshold_slider, stretch=1)
        slider_layout.addWidget(self._threshold_label)

        sub, card = _make_group(
            t("settings.general"),
            [
                _make_row(t("settings.theme"), self._theme_combo),
                _make_row(t("settings.chunk_size"), self._chunk_spin),
                _make_row(t("settings.max_workers"), self._workers_spin),
                _make_row(t("settings.threshold"), slider_container),
            ],
        )
        root_layout.addWidget(sub)
        root_layout.addWidget(card)

        # --- Save button -------------------------------------------------
        self._save_btn = PrimaryPushButton(FluentIcon.SAVE, t("settings.save"))
        self._save_btn.setFixedWidth(200)
        self._save_btn.clicked.connect(self._on_save_clicked)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self._save_btn)
        btn_layout.addStretch()
        root_layout.addLayout(btn_layout)

        # Bottom spacer
        root_layout.addStretch()

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def load_from_config(self, config: AppConfig) -> None:
        """Populate all input fields from *config*."""
        # OpenRouter
        self._openrouter_key.setText(config.openrouter_api_key)
        self._openrouter_url.setText(config.openrouter_base_url)
        self._openrouter_model.setText(config.openrouter_model)

        # Gemini
        self._gemini_key.setText(config.gemini_api_key)
        self._gemini_url.setText(config.gemini_base_url)

        # Qwen
        self._qwen_key.setText(config.qwen_api_key)
        self._qwen_url.setText(config.qwen_base_url)
        self._qwen_model.setText(config.qwen_model)

        # MinerU
        self._mineru_token.setText(config.mineru_api_token)

        # General - theme
        theme_map = {"light": 0, "dark": 1, "auto": 2}
        self._theme_combo.setCurrentIndex(theme_map.get(config.theme, 0))

        # General - numeric
        self._chunk_spin.setValue(config.default_chunk_size)
        self._workers_spin.setValue(config.default_max_workers)
        self._threshold_slider.setValue(config.default_similarity_threshold)
        self._threshold_label.setText(str(config.default_similarity_threshold))

    def save_to_config(self) -> AppConfig:
        """Read all fields and return an updated :class:`AppConfig`."""
        theme_values = ["light", "dark", "auto"]
        theme_index = self._theme_combo.currentIndex()

        return AppConfig(
            # OpenRouter
            openrouter_api_key=self._openrouter_key.text().strip(),
            openrouter_base_url=self._openrouter_url.text().strip(),
            openrouter_model=self._openrouter_model.text().strip(),
            # Gemini
            gemini_api_key=self._gemini_key.text().strip(),
            gemini_base_url=self._gemini_url.text().strip(),
            # Qwen
            qwen_api_key=self._qwen_key.text().strip(),
            qwen_base_url=self._qwen_url.text().strip(),
            qwen_model=self._qwen_model.text().strip(),
            # MinerU
            mineru_api_token=self._mineru_token.text().strip(),
            # General
            theme=theme_values[theme_index] if 0 <= theme_index < len(theme_values) else "light",
            default_chunk_size=self._chunk_spin.value(),
            default_max_workers=self._workers_spin.value(),
            default_similarity_threshold=self._threshold_slider.value(),
        )

    # -----------------------------------------------------------------
    # Slots
    # -----------------------------------------------------------------

    def _on_save_clicked(self) -> None:
        """Gather field values and emit :pyqtSignal:`save_requested`."""
        config = self.save_to_config()
        self.save_requested.emit(config)
