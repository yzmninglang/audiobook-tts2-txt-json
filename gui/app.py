"""
听书工坊 (Audiobook Workshop) - Application entry point.

Initializes the Qt application, loads configuration, applies theme and
language settings, and launches the main window.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QApplication
from qfluentwidgets import Theme, isDarkTheme, setTheme, setThemeColor

from gui.core.config import load_config
from gui.main_window import MainWindow
from gui.styles import FIXED_THEME_ACCENT_HEX, get_stylesheet


def _set_windows_app_user_model_id() -> None:
    """Set AppUserModelID so Windows taskbar uses our app icon."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "AudiobookWorkshop.Desktop"
        )
    except Exception:
        pass


def _apply_theme(theme_name: str) -> None:
    """Apply the application theme."""
    name = (theme_name or "light").lower()
    if name == "dark":
        theme = Theme.DARK
    elif name == "auto":
        theme = Theme.AUTO
    else:
        theme = Theme.LIGHT

    setTheme(theme, lazy=True)
    setThemeColor(FIXED_THEME_ACCENT_HEX, lazy=True)


def main() -> int:
    """Application entry point."""
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Windows taskbar icon
    _set_windows_app_user_model_id()

    app = QApplication(sys.argv)
    app.setApplicationName("听书工坊")
    app.setOrganizationName("AudiobookWorkshop")

    # Text clarity
    font = app.font()
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)

    # Load config
    config = load_config()

    # Apply theme
    _apply_theme(config.theme)
    app.setStyleSheet(get_stylesheet(dark=isDarkTheme()))

    # Application icon
    icon_path = Path(__file__).parent / "resources" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Create and show main window
    window = MainWindow(config)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
