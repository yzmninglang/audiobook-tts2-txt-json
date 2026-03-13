"""
听书工坊 (Audiobook Workshop) - Main window.

FluentWindow with sidebar navigation, lazy page loading, worker thread
management, and pipeline state coordination between pages.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QFileDialog
from qfluentwidgets import (
    FluentIcon,
    FluentWindow,
    InfoBar,
    InfoBarPosition,
    NavigationItemPosition,
    NavigationToolButton,
    Theme,
    isDarkTheme,
    qconfig,
    setCustomStyleSheet,
    setTheme,
    setThemeColor,
)

from gui.core.config import AppConfig, load_config, save_config
from gui.core.models import PipelineState
from gui.i18n import set_language, t
from gui.pages.import_page import ImportPage
from gui.styles import (
    DARK_PAGE_BACKGROUND_HEX,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    FIXED_PAGE_BACKGROUND_HEX,
    FIXED_THEME_ACCENT_HEX,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    TITLE_BAR_HEIGHT,
    get_display_scale,
    get_stylesheet,
    scale_px,
)

if TYPE_CHECKING:
    from gui.pages.chapter_split_page import ChapterSplitPage
    from gui.pages.json_gen_page import JsonGenPage
    from gui.pages.settings_page import SettingsPage
    from gui.pages.speaker_page import SpeakerPage


class MainWindow(FluentWindow):
    """Main application window with navigation and page management."""

    theme_changed = pyqtSignal(str)
    config_updated = pyqtSignal(list)

    def __init__(self, config: AppConfig | None = None):
        super().__init__()
        self.config = config or load_config()
        if self.config.theme not in {"light", "dark", "auto"}:
            self.config.theme = "light"

        self.pipeline_state = PipelineState()

        # Language
        set_language(self.config.language)

        # Apply theme
        self._apply_theme(apply_stylesheet=True)

        # Build import page immediately; others are lazy
        self._import_page = ImportPage(self)
        self._chapter_split_page: ChapterSplitPage | None = None
        self._json_gen_page: JsonGenPage | None = None
        self._speaker_page: SpeakerPage | None = None
        self._settings_page: SettingsPage | None = None

        self._nav_routes_added: set[str] = set()
        self._deferred_page_queue: list[str] = [
            "chapter_split",
            "json_gen",
            "speaker",
            "settings",
        ]
        self._deferred_bootstrap_started = False

        # Active workers (prevent GC)
        self._active_workers: list = []

        self._init_window()
        self._init_navigation()

        # Theme change detection
        qconfig.themeChanged.connect(self._on_theme_changed)

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _init_window(self):
        self.setWindowTitle("听书工坊")
        self.setMicaEffectEnabled(False)
        self.setCustomBackgroundColor(
            FIXED_PAGE_BACKGROUND_HEX, DARK_PAGE_BACKGROUND_HEX
        )

        screen = self.screen() or QApplication.primaryScreen()
        scale = get_display_scale(screen=screen)
        available = screen.availableGeometry() if screen else None

        preferred_w = scale_px(DEFAULT_WINDOW_WIDTH, scale=scale, min_value=DEFAULT_WINDOW_WIDTH)
        preferred_h = scale_px(DEFAULT_WINDOW_HEIGHT, scale=scale, min_value=DEFAULT_WINDOW_HEIGHT)
        min_w = scale_px(MIN_WINDOW_WIDTH, scale=scale, min_value=MIN_WINDOW_WIDTH)
        min_h = scale_px(MIN_WINDOW_HEIGHT, scale=scale, min_value=MIN_WINDOW_HEIGHT)

        if available:
            max_w = max(820, available.width() - scale_px(48, scale=scale, min_value=48))
            max_h = max(620, available.height() - scale_px(64, scale=scale, min_value=64))
            eff_min_w = min(min_w, max_w)
            eff_min_h = min(min_h, max_h)
            target_w = max(eff_min_w, min(preferred_w, max_w))
            target_h = max(eff_min_h, min(preferred_h, max_h))
            self.setMinimumSize(eff_min_w, eff_min_h)
            self.resize(target_w, target_h)
        else:
            self.setMinimumSize(min_w, min_h)
            self.resize(preferred_w, preferred_h)

        if hasattr(self, "titleBar") and self.titleBar is not None:
            self.titleBar.setFixedHeight(TITLE_BAR_HEIGHT)
            if hasattr(self, "widgetLayout") and self.widgetLayout is not None:
                self.widgetLayout.setContentsMargins(0, self.titleBar.height(), 0, 0)

        icon_path = Path(__file__).parent / "resources" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._apply_fixed_background()

    def _apply_fixed_background(self):
        bg_l = FIXED_PAGE_BACKGROUND_HEX
        bg_d = DARK_PAGE_BACKGROUND_HEX
        setCustomStyleSheet(
            self,
            f"FluentWindowBase {{ background-color: {bg_l}; }}",
            f"FluentWindowBase {{ background-color: {bg_d}; }}",
        )

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _init_navigation(self):
        # Import page (always loaded)
        self.addSubInterface(
            self._import_page, FluentIcon.FOLDER_ADD, t("nav.import")
        )
        self._nav_routes_added.add("import")

        # Theme toggle button at bottom
        self._theme_btn = NavigationToolButton(FluentIcon.CONSTRACT, self)
        self._theme_btn.clicked.connect(self._cycle_theme)
        self.navigationInterface.addWidget(
            "themeButton",
            self._theme_btn,
            onClick=self._cycle_theme,
            position=NavigationItemPosition.BOTTOM,
        )

    def _ensure_page(self, key: str, *, add_to_navigation: bool = True):
        """Create a page if it doesn't exist yet; optionally add to nav."""
        if key == "chapter_split" and self._chapter_split_page is None:
            from gui.pages.chapter_split_page import ChapterSplitPage

            self._chapter_split_page = ChapterSplitPage(self)
            self._connect_chapter_split_page()
            if add_to_navigation and key not in self._nav_routes_added:
                self.addSubInterface(
                    self._chapter_split_page, FluentIcon.CUT, t("nav.chapter_split")
                )
                self._nav_routes_added.add(key)

        elif key == "json_gen" and self._json_gen_page is None:
            from gui.pages.json_gen_page import JsonGenPage

            self._json_gen_page = JsonGenPage(self)
            self._connect_json_gen_page()
            if add_to_navigation and key not in self._nav_routes_added:
                self.addSubInterface(
                    self._json_gen_page, FluentIcon.ROBOT, t("nav.json_gen")
                )
                self._nav_routes_added.add(key)

        elif key == "speaker" and self._speaker_page is None:
            from gui.pages.speaker_page import SpeakerPage

            self._speaker_page = SpeakerPage(self)
            self._connect_speaker_page()
            if add_to_navigation and key not in self._nav_routes_added:
                self.addSubInterface(
                    self._speaker_page, FluentIcon.PEOPLE, t("nav.speaker")
                )
                self._nav_routes_added.add(key)

        elif key == "settings" and self._settings_page is None:
            from gui.pages.settings_page import SettingsPage

            self._settings_page = SettingsPage(self)
            self._settings_page.load_from_config(self.config)
            self._connect_settings_page()
            if add_to_navigation and key not in self._nav_routes_added:
                self.addSubInterface(
                    self._settings_page,
                    FluentIcon.SETTING,
                    t("nav.settings"),
                    position=NavigationItemPosition.BOTTOM,
                )
                self._nav_routes_added.add(key)

    # ------------------------------------------------------------------
    # Lazy page bootstrap (AnkiSmart pattern)
    # ------------------------------------------------------------------

    def bootstrap_secondary_pages(self):
        if not self._deferred_bootstrap_started:
            self._deferred_bootstrap_started = True
            QTimer.singleShot(0, self._bootstrap_next_page)

    def _bootstrap_next_page(self):
        if not self._deferred_page_queue:
            return
        key = self._deferred_page_queue.pop(0)
        self._ensure_page(key, add_to_navigation=True)
        if self._deferred_page_queue:
            QTimer.singleShot(0, self._bootstrap_next_page)

    # ------------------------------------------------------------------
    # Signal connections
    # ------------------------------------------------------------------

    def _connect_import_page(self):
        """Wire import page signals (called from __init__ since page is immediate)."""
        self._import_page.file_selected.connect(self._on_file_selected)
        self._import_page.convert_requested.connect(self._on_import_convert)
        self._import_page.content_ready.connect(self._on_import_content_ready)

    def _connect_chapter_split_page(self):
        self._chapter_split_page.split_requested.connect(self._on_split_requested)
        self._chapter_split_page.next_step.connect(self._on_split_next)

    def _connect_json_gen_page(self):
        self._json_gen_page.generate_requested.connect(self._on_generate_requested)

    def _connect_speaker_page(self):
        self._speaker_page.extract_requested.connect(self._on_extract_speakers)
        self._speaker_page.classify_requested.connect(self._on_classify_speakers)
        self._speaker_page.apply_requested.connect(self._on_apply_classifications)
        self._speaker_page.export_requested.connect(self._on_export_json)

    def _connect_settings_page(self):
        self._settings_page.save_requested.connect(self._on_save_settings)

    # ------------------------------------------------------------------
    # Import page handlers
    # ------------------------------------------------------------------

    def _on_file_selected(self, path: str):
        """Store the selected file in pipeline state."""
        from gui.core.models import FileType, ImportedFile

        p = Path(path)
        ext = p.suffix.lower().lstrip(".")
        try:
            file_type = FileType(ext)
        except ValueError:
            file_type = FileType.TXT

        self.pipeline_state.imported_file = ImportedFile(
            path=p,
            file_type=file_type,
            size_bytes=p.stat().st_size,
            name=p.stem,
        )
        self.pipeline_state.book_name = p.stem

    def _on_import_convert(self):
        """Handle PDF conversion via MinerU worker."""
        state = self.pipeline_state
        if not state.imported_file:
            return

        file_path = str(state.imported_file.path)
        token = self.config.mineru_api_token

        if not token:
            InfoBar.warning(
                "MinerU",
                "请先在设置页配置 MinerU API Token",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )
            return

        from gui.workers.mineru_worker import MineruWorker

        worker = MineruWorker(file_path, token)
        worker.progress.connect(self._import_page.set_progress)
        worker.finished.connect(self._on_mineru_finished)
        worker.error.connect(self._on_mineru_error)
        self._active_workers.append(worker)
        worker.finished.connect(lambda _: self._cleanup_worker(worker))
        worker.error.connect(lambda _: self._cleanup_worker(worker))
        worker.start()

    def _on_mineru_finished(self, markdown: str):
        book_name = self.pipeline_state.book_name or "untitled"
        self._on_import_content_ready(markdown, book_name)

    def _on_mineru_error(self, msg: str):
        InfoBar.error("MinerU", msg, parent=self, position=InfoBarPosition.TOP, duration=5000)
        self._import_page.set_progress(0)
        self._import_page.on_convert_finished(False, msg)

    def _on_import_content_ready(self, content: str, book_name: str):
        """Markdown content is ready — store and switch to split page."""
        self.pipeline_state.markdown_content = content
        self.pipeline_state.book_name = book_name
        self.pipeline_state.output_dir = f"{book_name}_chapters"

        self._ensure_page("chapter_split")
        if self._chapter_split_page:
            self._chapter_split_page.update_content(content)
            self.switchTo(self._chapter_split_page)

        InfoBar.success(
            t("common.success"),
            t("import.convert_success"),
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )

    # ------------------------------------------------------------------
    # Chapter split handlers
    # ------------------------------------------------------------------

    def _on_split_requested(self, content: str, titles: list, threshold: int):
        from gui.workers.split_worker import SplitWorker

        worker = SplitWorker(content, titles, threshold)
        worker.progress.connect(self._chapter_split_page.set_progress)
        worker.finished.connect(self._on_split_finished)
        worker.error.connect(self._on_split_error)
        self._active_workers.append(worker)
        worker.finished.connect(lambda _: self._cleanup_worker(worker))
        worker.error.connect(lambda _: self._cleanup_worker(worker))
        worker.start()

    def _on_split_finished(self, chapters: list):
        self.pipeline_state.chapters = []
        from gui.core.models import ChapterInfo

        for ch in chapters:
            self.pipeline_state.chapters.append(
                ChapterInfo(
                    index=ch["index"],
                    title=ch["title"],
                    content=ch["content"],
                    line_start=ch.get("line_start", 0),
                    line_end=ch.get("line_end", 0),
                )
            )

        if self._chapter_split_page:
            chapters_tuples = [(ch["title"], ch["content"]) for ch in chapters]
            self._chapter_split_page.set_chapters(chapters_tuples)

        InfoBar.success(
            t("common.success"),
            t("split.split_success").replace("{count}", str(len(chapters)))
            if "{count}" in t("split.split_success")
            else f"{t('split.split_success')} ({len(chapters)})",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )

    def _on_split_error(self, msg: str):
        InfoBar.error(t("common.error"), msg, parent=self, position=InfoBarPosition.TOP, duration=5000)

    def _on_split_next(self):
        """Switch to JSON gen page after splitting."""
        self._ensure_page("json_gen")
        if self._json_gen_page:
            chapter_names = [
                f"P{ch.index:02d}_{ch.title}" for ch in self.pipeline_state.chapters
            ]
            self._json_gen_page.update_chapters(chapter_names)
            self.switchTo(self._json_gen_page)

    # ------------------------------------------------------------------
    # JSON gen handlers
    # ------------------------------------------------------------------

    def _on_generate_requested(self, selected_indices, provider, workers, chunk_size):
        from gui.workers.json_gen_worker import JsonGenWorker

        # Map provider name to config
        provider_lower = provider.lower()
        if provider_lower == "openrouter":
            api_key = self.config.openrouter_api_key
            base_url = self.config.openrouter_base_url
            model = self.config.openrouter_model
        elif provider_lower == "gemini":
            api_key = self.config.gemini_api_key
            base_url = self.config.gemini_base_url + "/v1beta/"
            model = "gemini-2.5-flash"
        elif provider_lower == "qwen":
            api_key = self.config.qwen_api_key
            base_url = self.config.qwen_base_url
            model = self.config.qwen_model
        else:
            api_key = self.config.openrouter_api_key
            base_url = self.config.openrouter_base_url
            model = self.config.openrouter_model

        if not api_key:
            InfoBar.warning(
                t("common.warning"),
                f"请先在设置页配置 {provider} API Key",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )
            return

        # Build chapter dicts for the worker
        chapters_data = []
        for ch in self.pipeline_state.chapters:
            chapters_data.append({
                "index": ch.index,
                "title": ch.title,
                "content": ch.content,
            })

        # Adjust selected indices: UI is 0-based, chapters are 1-based
        actual_indices = [self.pipeline_state.chapters[i].index for i in selected_indices]

        worker = JsonGenWorker(
            chapters=chapters_data,
            selected_indices=actual_indices,
            provider=provider_lower,
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_workers=workers,
            chunk_size=chunk_size,
        )
        worker.chapter_progress.connect(self._json_gen_page.update_chapter_status)
        worker.log_message.connect(self._json_gen_page.append_log)
        worker.finished.connect(self._on_gen_finished)
        worker.error.connect(self._on_gen_error)
        self._active_workers.append(worker)
        worker.finished.connect(lambda _: self._cleanup_worker(worker))
        worker.error.connect(lambda _: self._cleanup_worker(worker))
        worker.start()

    def _on_gen_finished(self, results: list):
        from gui.core.models import ChapterResult, TTSEntry

        self.pipeline_state.chapter_results = []
        for r in results:
            entries = []
            for e in r.get("entries", []):
                entries.append(TTSEntry(
                    speaker=e.get("speaker", "旁白"),
                    content=e.get("content", ""),
                    emo_vector=e.get("emo_vector", [0.0] * 8),
                    delay=e.get("delay", 500),
                ))
            self.pipeline_state.chapter_results.append(ChapterResult(
                chapter_index=r["chapter_index"],
                chapter_title=r["chapter_title"],
                entries=entries,
                status=r.get("status", "done"),
                error_message=r.get("error_message", ""),
            ))

        InfoBar.success(
            t("common.success"),
            t("gen.gen_success"),
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )

    def _on_gen_error(self, msg: str):
        InfoBar.error(t("common.error"), msg, parent=self, position=InfoBarPosition.TOP, duration=5000)

    # ------------------------------------------------------------------
    # Speaker handlers
    # ------------------------------------------------------------------

    def _on_extract_speakers(self):
        if not self.pipeline_state.chapter_results:
            InfoBar.warning(
                t("common.warning"),
                t("speaker.no_results"),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )
            return

        from gui.workers.speaker_worker import SpeakerExtractWorker

        cr_dicts = []
        for cr in self.pipeline_state.chapter_results:
            cr_dicts.append({"entries": [e.model_dump() for e in cr.entries]})

        worker = SpeakerExtractWorker(cr_dicts)
        worker.finished.connect(self._on_speakers_extracted)
        worker.error.connect(lambda msg: InfoBar.error(
            t("common.error"), msg, parent=self, position=InfoBarPosition.TOP, duration=5000
        ))
        self._active_workers.append(worker)
        worker.finished.connect(lambda _: self._cleanup_worker(worker))
        worker.error.connect(lambda _: self._cleanup_worker(worker))
        worker.start()

    def _on_speakers_extracted(self, speakers: list):
        from gui.core.models import SpeakerInfo

        self.pipeline_state.speakers = [
            SpeakerInfo(name=name, count=count) for name, count in speakers
        ]
        if self._speaker_page:
            self._speaker_page.update_speakers(speakers)

    def _on_classify_speakers(self):
        if not self.pipeline_state.speakers:
            return

        from gui.workers.speaker_worker import SpeakerClassifyWorker

        names = [s.name for s in self.pipeline_state.speakers]
        worker = SpeakerClassifyWorker(
            names,
            api_key=self.config.openrouter_api_key,
            base_url=self.config.openrouter_base_url,
            model=self.config.openrouter_model,
        )
        worker.finished.connect(self._on_classify_finished)
        worker.error.connect(lambda msg: InfoBar.error(
            t("common.error"), msg, parent=self, position=InfoBarPosition.TOP, duration=5000
        ))
        self._active_workers.append(worker)
        worker.finished.connect(lambda _: self._cleanup_worker(worker))
        worker.error.connect(lambda _: self._cleanup_worker(worker))
        worker.start()

    def _on_classify_finished(self, classifications: dict):
        self.pipeline_state.classifications = classifications
        if self._speaker_page:
            self._speaker_page.set_classifications(classifications)

    def _on_apply_classifications(self, classifications: dict):
        if not self.pipeline_state.chapter_results:
            return

        from gui.workers.speaker_worker import SpeakerReplaceWorker

        cr_dicts = []
        for cr in self.pipeline_state.chapter_results:
            cr_dicts.append({
                "chapter_index": cr.chapter_index,
                "chapter_title": cr.chapter_title,
                "entries": [e.model_dump() for e in cr.entries],
                "status": cr.status,
            })

        worker = SpeakerReplaceWorker(cr_dicts, classifications)
        worker.finished.connect(self._on_replace_finished)
        worker.error.connect(lambda msg: InfoBar.error(
            t("common.error"), msg, parent=self, position=InfoBarPosition.TOP, duration=5000
        ))
        self._active_workers.append(worker)
        worker.finished.connect(lambda _: self._cleanup_worker(worker))
        worker.error.connect(lambda _: self._cleanup_worker(worker))
        worker.start()

    def _on_replace_finished(self, updated: list):
        # Update pipeline state
        self._on_gen_finished(updated)

        if self._speaker_page:
            cr_dicts = []
            for cr in self.pipeline_state.chapter_results:
                cr_dicts.append({
                    "entries": [e.model_dump() for e in cr.entries],
                })
            self._speaker_page.update_preview(cr_dicts)

        InfoBar.success(
            t("common.success"),
            t("speaker.applying") + " - 完成",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )

    def _on_export_json(self, output_dir: str):
        """Export all chapter results as JSON files."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        for cr in self.pipeline_state.chapter_results:
            filename = f"P{cr.chapter_index:02d}_{cr.chapter_title}.json"
            entries = [e.model_dump() for e in cr.entries]
            (out / filename).write_text(
                json.dumps(entries, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        InfoBar.success(
            t("common.success"),
            f"{t('speaker.export_success')}: {output_dir}",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=5000,
        )

    # ------------------------------------------------------------------
    # Settings handler
    # ------------------------------------------------------------------

    def _on_save_settings(self, new_config):
        old_theme = self.config.theme
        self.config = new_config
        save_config(self.config)

        if self.config.theme != old_theme:
            self._apply_theme(apply_stylesheet=True)

        InfoBar.success(
            t("common.success"),
            t("settings.save_success"),
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )

    # ------------------------------------------------------------------
    # Theme management
    # ------------------------------------------------------------------

    def _apply_theme(self, *, apply_stylesheet: bool = False):
        name = self.config.theme
        if name == "dark":
            setTheme(Theme.DARK, lazy=True)
        elif name == "auto":
            setTheme(Theme.AUTO, lazy=True)
        else:
            setTheme(Theme.LIGHT, lazy=True)

        setThemeColor(FIXED_THEME_ACCENT_HEX, lazy=True)

        if apply_stylesheet:
            app = QApplication.instance()
            if app:
                css = get_stylesheet(dark=isDarkTheme())
                app.setStyleSheet(css)

    def _cycle_theme(self):
        cycle = {"light": "dark", "dark": "auto", "auto": "light"}
        self.config.theme = cycle.get(self.config.theme, "light")
        self._apply_theme(apply_stylesheet=True)
        self._apply_fixed_background()
        save_config(self.config)
        self.theme_changed.emit(self.config.theme)

    def _on_theme_changed(self, theme):
        app = QApplication.instance()
        if app:
            css = get_stylesheet(dark=isDarkTheme())
            app.setStyleSheet(css)
        self._apply_fixed_background()

    # ------------------------------------------------------------------
    # Worker lifecycle
    # ------------------------------------------------------------------

    def _cleanup_worker(self, worker):
        if worker in self._active_workers:
            self._active_workers.remove(worker)

    # ------------------------------------------------------------------
    # Override show to connect import page and kick off lazy loading
    # ------------------------------------------------------------------

    def show(self):
        super().show()
        self._connect_import_page()
        self.bootstrap_secondary_pages()
