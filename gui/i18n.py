"""
听书工坊 (Audiobook Workshop) - Internationalization module.

Provides Chinese (zh) and English (en) translations with a simple
key-based lookup.  Chinese is the primary / default language.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_current_language: str = "zh"


def set_language(lang: str) -> None:
    """Set the active UI language (``"zh"`` or ``"en"``)."""
    global _current_language
    _current_language = lang


def get_current_language() -> str:
    """Return the currently active language code."""
    return _current_language


# ---------------------------------------------------------------------------
# Translation table
# ---------------------------------------------------------------------------
TRANSLATIONS: dict[str, dict[str, str]] = {
    # ==================================================================
    # Navigation
    # ==================================================================
    "nav.import": {
        "zh": "导入",
        "en": "Import",
    },
    "nav.chapter_split": {
        "zh": "章节分割",
        "en": "Chapter Split",
    },
    "nav.json_gen": {
        "zh": "JSON 生成",
        "en": "JSON Generation",
    },
    "nav.speaker": {
        "zh": "说话人",
        "en": "Speaker",
    },
    "nav.settings": {
        "zh": "设置",
        "en": "Settings",
    },

    # ==================================================================
    # Import page
    # ==================================================================
    "import.title": {
        "zh": "导入文件",
        "en": "Import File",
    },
    "import.drag_hint": {
        "zh": "拖拽文件到此处，或点击选择文件",
        "en": "Drag file here, or click to select",
    },
    "import.select_file": {
        "zh": "选择文件",
        "en": "Select File",
    },
    "import.start_convert": {
        "zh": "开始转换",
        "en": "Start Conversion",
    },
    "import.converting": {
        "zh": "正在转换...",
        "en": "Converting...",
    },
    "import.file_name": {
        "zh": "文件名",
        "en": "File Name",
    },
    "import.file_size": {
        "zh": "文件大小",
        "en": "File Size",
    },
    "import.file_type": {
        "zh": "文件类型",
        "en": "File Type",
    },
    "import.convert_success": {
        "zh": "转换成功",
        "en": "Conversion Successful",
    },
    "import.convert_error": {
        "zh": "转换失败",
        "en": "Conversion Failed",
    },
    "import.no_file": {
        "zh": "请先选择文件",
        "en": "Please select a file first",
    },
    "import.reading_file": {
        "zh": "正在读取文件...",
        "en": "Reading file...",
    },

    # ==================================================================
    # Chapter split page
    # ==================================================================
    "split.title": {
        "zh": "章节分割",
        "en": "Chapter Split",
    },
    "split.chapter_list": {
        "zh": "章节目录",
        "en": "Chapter List",
    },
    "split.chapter_list_hint": {
        "zh": "请粘贴或输入章节目录，每行一个章节标题",
        "en": "Paste or enter chapter titles, one per line",
    },
    "split.load_from_file": {
        "zh": "从文件加载",
        "en": "Load from File",
    },
    "split.threshold": {
        "zh": "相似度阈值",
        "en": "Similarity Threshold",
    },
    "split.start_split": {
        "zh": "开始分割",
        "en": "Start Split",
    },
    "split.splitting": {
        "zh": "正在分割...",
        "en": "Splitting...",
    },
    "split.split_success": {
        "zh": "分割成功",
        "en": "Split Successful",
    },
    "split.content_preview": {
        "zh": "内容预览",
        "en": "Content Preview",
    },
    "split.split_result": {
        "zh": "分割结果",
        "en": "Split Result",
    },
    "split.no_content": {
        "zh": "暂无内容",
        "en": "No content available",
    },
    "split.next_step": {
        "zh": "下一步",
        "en": "Next Step",
    },
    "split.chapter_count": {
        "zh": "章节数量",
        "en": "Chapter Count",
    },

    # ==================================================================
    # JSON generation page
    # ==================================================================
    "gen.title": {
        "zh": "JSON 生成",
        "en": "JSON Generation",
    },
    "gen.provider": {
        "zh": "服务提供商",
        "en": "Provider",
    },
    "gen.workers": {
        "zh": "并发数",
        "en": "Workers",
    },
    "gen.chunk_size": {
        "zh": "分块大小",
        "en": "Chunk Size",
    },
    "gen.select_all": {
        "zh": "全选",
        "en": "Select All",
    },
    "gen.deselect_all": {
        "zh": "取消全选",
        "en": "Deselect All",
    },
    "gen.start_gen": {
        "zh": "开始生成",
        "en": "Start Generation",
    },
    "gen.generating": {
        "zh": "正在生成...",
        "en": "Generating...",
    },
    "gen.gen_success": {
        "zh": "生成成功",
        "en": "Generation Successful",
    },
    "gen.gen_error": {
        "zh": "生成失败",
        "en": "Generation Failed",
    },
    "gen.progress": {
        "zh": "进度",
        "en": "Progress",
    },
    "gen.log": {
        "zh": "日志",
        "en": "Log",
    },
    "gen.no_chapters": {
        "zh": "没有可用的章节",
        "en": "No chapters available",
    },
    "gen.chapter_done": {
        "zh": "章节完成",
        "en": "Chapter Done",
    },
    "gen.chapter_error": {
        "zh": "章节出错",
        "en": "Chapter Error",
    },
    "gen.chunk_progress": {
        "zh": "分块进度",
        "en": "Chunk Progress",
    },
    "gen.chunk_size_suffix": {
        "zh": "字符",
        "en": "chars",
    },

    # ==================================================================
    # Speaker page
    # ==================================================================
    "speaker.title": {
        "zh": "说话人管理",
        "en": "Speaker Management",
    },
    "speaker.extract": {
        "zh": "提取说话人",
        "en": "Extract Speakers",
    },
    "speaker.ai_classify": {
        "zh": "AI 分类",
        "en": "AI Classify",
    },
    "speaker.apply": {
        "zh": "应用分类",
        "en": "Apply Classification",
    },
    "speaker.export": {
        "zh": "导出",
        "en": "Export",
    },
    "speaker.name": {
        "zh": "说话人名称",
        "en": "Speaker Name",
    },
    "speaker.count": {
        "zh": "出现次数",
        "en": "Count",
    },
    "speaker.classification": {
        "zh": "分类",
        "en": "Classification",
    },
    "speaker.preview": {
        "zh": "预览",
        "en": "Preview",
    },
    "speaker.extracting": {
        "zh": "正在提取说话人...",
        "en": "Extracting speakers...",
    },
    "speaker.classifying": {
        "zh": "正在进行 AI 分类...",
        "en": "AI classifying...",
    },
    "speaker.applying": {
        "zh": "正在应用分类...",
        "en": "Applying classification...",
    },
    "speaker.export_success": {
        "zh": "导出成功",
        "en": "Export Successful",
    },
    "speaker.no_results": {
        "zh": "暂无结果",
        "en": "No results",
    },
    "speaker.categories": {
        "zh": "少男/少女/中男/中女/老男/老女",
        "en": "Young Male/Young Female/Middle-aged Male/Middle-aged Female/Elder Male/Elder Female",
    },

    # ==================================================================
    # Settings page
    # ==================================================================
    "settings.title": {
        "zh": "设置",
        "en": "Settings",
    },
    "settings.openrouter": {
        "zh": "OpenRouter",
        "en": "OpenRouter",
    },
    "settings.gemini": {
        "zh": "Gemini",
        "en": "Gemini",
    },
    "settings.qwen": {
        "zh": "通义千问",
        "en": "Qwen",
    },
    "settings.mineru": {
        "zh": "MinerU",
        "en": "MinerU",
    },
    "settings.general": {
        "zh": "通用设置",
        "en": "General",
    },
    "settings.api_key": {
        "zh": "API 密钥",
        "en": "API Key",
    },
    "settings.base_url": {
        "zh": "接口地址",
        "en": "Base URL",
    },
    "settings.model": {
        "zh": "模型",
        "en": "Model",
    },
    "settings.api_token": {
        "zh": "API Token",
        "en": "API Token",
    },
    "settings.theme": {
        "zh": "主题",
        "en": "Theme",
    },
    "settings.theme_light": {
        "zh": "浅色",
        "en": "Light",
    },
    "settings.theme_dark": {
        "zh": "深色",
        "en": "Dark",
    },
    "settings.theme_auto": {
        "zh": "跟随系统",
        "en": "Auto",
    },
    "settings.chunk_size": {
        "zh": "分块大小",
        "en": "Chunk Size",
    },
    "settings.max_workers": {
        "zh": "最大并发数",
        "en": "Max Workers",
    },
    "settings.threshold": {
        "zh": "相似度阈值",
        "en": "Similarity Threshold",
    },
    "settings.save": {
        "zh": "保存设置",
        "en": "Save Settings",
    },
    "settings.save_success": {
        "zh": "设置已保存",
        "en": "Settings Saved",
    },

    # ==================================================================
    # Common
    # ==================================================================
    "common.cancel": {
        "zh": "取消",
        "en": "Cancel",
    },
    "common.confirm": {
        "zh": "确认",
        "en": "Confirm",
    },
    "common.error": {
        "zh": "错误",
        "en": "Error",
    },
    "common.success": {
        "zh": "成功",
        "en": "Success",
    },
    "common.warning": {
        "zh": "警告",
        "en": "Warning",
    },
    "common.next": {
        "zh": "下一步",
        "en": "Next",
    },
    "common.prev": {
        "zh": "上一步",
        "en": "Previous",
    },
}


# ---------------------------------------------------------------------------
# Translation lookup
# ---------------------------------------------------------------------------
def t(key: str, lang: str | None = None) -> str:
    """Return the translated string for *key*.

    Parameters
    ----------
    key : str
        Dot-separated translation key (e.g. ``"nav.import"``).
    lang : str or None
        Language override.  When *None*, uses the module-level
        ``_current_language``.

    Returns
    -------
    str
        The translated text.  Falls back to Chinese (``"zh"``),
        then to the raw *key* if no translation is found.
    """
    if lang is None:
        lang = _current_language

    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key

    # Try requested language, fall back to zh, then to key
    text = entry.get(lang)
    if text is not None:
        return text

    text = entry.get("zh")
    if text is not None:
        return text

    return key
