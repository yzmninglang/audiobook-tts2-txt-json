"""
听书工坊 (Audiobook Workshop) - Styling system.

Provides color constants, spacing, font sizes, window dimensions,
scaling utilities, and dynamic QSS stylesheet generation for
light and dark themes.
"""

from __future__ import annotations

from PyQt6.QtGui import QFont, QScreen
from PyQt6.QtWidgets import QApplication
from qfluentwidgets import isDarkTheme

# ---------------------------------------------------------------------------
# Color constants
# ---------------------------------------------------------------------------
FIXED_THEME_ACCENT_HEX = "#2563eb"
FIXED_PAGE_BACKGROUND_HEX = "#f5f7fb"
DARK_PAGE_BACKGROUND_HEX = "#202020"


class Colors:
    """Light-theme palette."""
    BACKGROUND = "#f5f7fb"
    SURFACE = "#ffffff"
    BORDER = "#e5e7eb"
    TEXT_PRIMARY = "#111827"
    TEXT_SECONDARY = "#6b7280"
    ACCENT = FIXED_THEME_ACCENT_HEX


class DarkColors:
    """Dark-theme palette."""
    BACKGROUND = "#202020"
    SURFACE = "#2b2b2b"
    BORDER = "#3a3a3a"
    TEXT_PRIMARY = "#e6e6e6"
    TEXT_SECONDARY = "#a6a6a6"
    ACCENT = FIXED_THEME_ACCENT_HEX


# ---------------------------------------------------------------------------
# Spacing
# ---------------------------------------------------------------------------
SPACING_SMALL = 8
SPACING_MEDIUM = 12
SPACING_LARGE = 20
SPACING_XLARGE = 24

# ---------------------------------------------------------------------------
# Margins
# ---------------------------------------------------------------------------
MARGIN_STANDARD = 20
MARGIN_SMALL = 10
MARGIN_LARGE = 30

# ---------------------------------------------------------------------------
# Font sizes
# ---------------------------------------------------------------------------
FONT_SIZE_SMALL = 12
FONT_SIZE_MEDIUM = 14
FONT_SIZE_LARGE = 16
FONT_SIZE_PAGE_TITLE = 22

# ---------------------------------------------------------------------------
# Window dimensions
# ---------------------------------------------------------------------------
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 900
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 540
TITLE_BAR_HEIGHT = 30

# ---------------------------------------------------------------------------
# Drag-and-drop area QSS
# ---------------------------------------------------------------------------
DRAG_DROP_AREA_STYLE = f"""
    QFrame#dragDropArea {{
        border: 2px dashed {Colors.BORDER};
        border-radius: 12px;
        background-color: {Colors.SURFACE};
    }}
    QFrame#dragDropArea:hover {{
        border-color: {Colors.ACCENT};
        background-color: rgba(37, 99, 235, 0.04);
    }}
"""

DRAG_DROP_AREA_STYLE_DARK = f"""
    QFrame#dragDropArea {{
        border: 2px dashed {DarkColors.BORDER};
        border-radius: 12px;
        background-color: {DarkColors.SURFACE};
    }}
    QFrame#dragDropArea:hover {{
        border-color: {DarkColors.ACCENT};
        background-color: rgba(37, 99, 235, 0.10);
    }}
"""


# ---------------------------------------------------------------------------
# Display scaling utilities
# ---------------------------------------------------------------------------
def get_display_scale(*, screen: QScreen | None = None) -> float:
    """Return the current display scale factor (e.g. 1.0, 1.25, 1.5, 2.0).

    Falls back to 1.0 if no application or screen is available.
    """
    if screen is not None:
        return screen.devicePixelRatio()
    app = QApplication.instance()
    if app is None:
        return 1.0
    screen = app.primaryScreen()
    if screen is None:
        return 1.0
    return screen.devicePixelRatio()


def scale_px(value: int, *, scale: float | None = None, min_value: int = 0) -> int:
    """Scale a pixel value according to the current display DPI.

    Parameters
    ----------
    value : int
        The base pixel value to scale.
    scale : float or None
        Explicit scale factor. If *None*, auto-detected.
    min_value : int
        Minimum return value (floor).
    """
    if scale is None:
        scale = get_display_scale()
    return max(min_value, int(value * scale))


def scale_text_px(value: int) -> int:
    """Scale a text pixel size according to the current display DPI.

    Uses a slightly dampened factor so text does not become
    disproportionately large on high-DPI screens.
    """
    factor = get_display_scale()
    dampened = 1.0 + (factor - 1.0) * 0.7
    return int(value * dampened)


# ---------------------------------------------------------------------------
# Dynamic QSS stylesheet
# ---------------------------------------------------------------------------
def get_page_background_color(dark: bool | None = None) -> str:
    """Return the page background hex color for the current or specified theme.

    Parameters
    ----------
    dark : bool or None
        If *None*, auto-detect via ``isDarkTheme()``.
    """
    if dark is None:
        dark = isDarkTheme()
    return DARK_PAGE_BACKGROUND_HEX if dark else FIXED_PAGE_BACKGROUND_HEX


def get_stylesheet(dark: bool = False) -> str:
    """Build and return the full application QSS stylesheet.

    Parameters
    ----------
    dark : bool
        When *True*, use the dark palette; otherwise use light.
    """
    c = DarkColors if dark else Colors

    # Accent hover / pressed variants
    accent_hover = "#1d4ed8"
    accent_pressed = "#1e40af"

    return f"""
        /* ---- Page-level background ---- */
        QWidget#pageContainer,
        QWidget[objectName^="page"] {{
            background-color: {c.BACKGROUND};
        }}

        /* ---- Labels ---- */
        QLabel {{
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
        }}
        QLabel#secondaryLabel {{
            color: {c.TEXT_SECONDARY};
        }}
        QLabel#pageTitle {{
            font-size: {FONT_SIZE_PAGE_TITLE}px;
            font-weight: 600;
            color: {c.TEXT_PRIMARY};
            background-color: transparent;
        }}

        /* ---- Line edits / text areas ---- */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {c.SURFACE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: {FONT_SIZE_MEDIUM}px;
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {c.ACCENT};
        }}

        /* ---- Buttons ---- */
        QPushButton {{
            background-color: {c.ACCENT};
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 8px 20px;
            font-size: {FONT_SIZE_MEDIUM}px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {accent_hover};
        }}
        QPushButton:pressed {{
            background-color: {accent_pressed};
        }}
        QPushButton:disabled {{
            background-color: {c.BORDER};
            color: {c.TEXT_SECONDARY};
        }}
        QPushButton#secondaryButton {{
            background-color: {c.SURFACE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
        }}
        QPushButton#secondaryButton:hover {{
            background-color: {c.BORDER};
        }}

        /* ---- ComboBox ---- */
        QComboBox {{
            background-color: {c.SURFACE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: {FONT_SIZE_MEDIUM}px;
        }}
        QComboBox:hover {{
            border-color: {c.ACCENT};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {c.SURFACE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            selection-background-color: {c.ACCENT};
            selection-color: #ffffff;
        }}

        /* ---- SpinBox ---- */
        QSpinBox, QDoubleSpinBox {{
            background-color: {c.SURFACE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: {FONT_SIZE_MEDIUM}px;
        }}
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {c.ACCENT};
        }}

        /* ---- Scrollbars (hidden) ---- */
        QScrollBar:vertical {{
            width: 0px;
            background: transparent;
        }}
        QScrollBar:horizontal {{
            height: 0px;
            background: transparent;
        }}
        QScrollBar::handle:vertical,
        QScrollBar::handle:horizontal {{
            background: transparent;
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical,
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            height: 0px;
            width: 0px;
        }}

        /* ---- Scroll area ---- */
        QScrollArea {{
            background-color: transparent;
            border: none;
        }}
        QScrollArea > QWidget > QWidget {{
            background-color: transparent;
        }}

        /* ---- Progress bar ---- */
        QProgressBar {{
            background-color: {c.BORDER};
            border: none;
            border-radius: 4px;
            height: 8px;
            text-align: center;
            font-size: {FONT_SIZE_SMALL}px;
            color: {c.TEXT_SECONDARY};
        }}
        QProgressBar::chunk {{
            background-color: {c.ACCENT};
            border-radius: 4px;
        }}

        /* ---- Table / Tree / List ---- */
        QTableWidget, QTreeWidget, QListWidget {{
            background-color: {c.SURFACE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: 6px;
            font-size: {FONT_SIZE_MEDIUM}px;
        }}
        QTableWidget::item:selected,
        QTreeWidget::item:selected,
        QListWidget::item:selected {{
            background-color: {c.ACCENT};
            color: #ffffff;
        }}
        QHeaderView::section {{
            background-color: {c.SURFACE};
            color: {c.TEXT_PRIMARY};
            border: none;
            border-bottom: 1px solid {c.BORDER};
            padding: 6px;
            font-size: {FONT_SIZE_MEDIUM}px;
            font-weight: 500;
        }}

        /* ---- Group box ---- */
        QGroupBox {{
            background-color: {c.SURFACE};
            border: 1px solid {c.BORDER};
            border-radius: 8px;
            margin-top: 16px;
            padding-top: 20px;
            font-size: {FONT_SIZE_MEDIUM}px;
            color: {c.TEXT_PRIMARY};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: {c.TEXT_PRIMARY};
        }}

        /* ---- ToolTip ---- */
        QToolTip {{
            background-color: {c.SURFACE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: {FONT_SIZE_SMALL}px;
        }}
    """
