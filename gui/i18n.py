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
    "nav.polish": {
        "zh": "文本润色",
        "en": "Text Polish",
    },
    "nav.speaker": {
        "zh": "说话人",
        "en": "Speaker",
    },
    "nav.settings": {
        "zh": "设置",
        "en": "Settings",
    },
    "nav.ocr_preview": {
        "zh": "OCR 预览",
        "en": "OCR Preview",
    },
    "nav.tts": {
        "zh": "语音合成",
        "en": "TTS Synthesis",
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
    # OCR Preview page
    # ==================================================================
    "ocr_preview.title": {
        "zh": "OCR 预览与编辑",
        "en": "OCR Preview & Edit",
    },
    "ocr_preview.save_md": {
        "zh": "保存为 MD",
        "en": "Save as MD",
    },
    "ocr_preview.continue_split": {
        "zh": "继续分割",
        "en": "Continue to Split",
    },
    "ocr_preview.load_history": {
        "zh": "从历史加载",
        "en": "Load from History",
    },
    "ocr_preview.history_title": {
        "zh": "历史记录",
        "en": "History",
    },
    "ocr_preview.no_history": {
        "zh": "暂无历史记录",
        "en": "No history records",
    },
    "ocr_preview.save_success": {
        "zh": "Markdown 已保存",
        "en": "Markdown saved",
    },
    "ocr_preview.delete_confirm": {
        "zh": "确认删除此历史记录？",
        "en": "Delete this history entry?",
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
    # Text polish page
    # ==================================================================
    "polish.title": {
        "zh": "文本润色",
        "en": "Text Polish",
    },
    "polish.hint": {
        "zh": "在不改动主要内容的前提下，把表格、数字与排版标记改写为适合朗读的口播稿。",
        "en": "Rewrite tables, numbers and markup into a listenable script — without changing the content.",
    },
    "polish.rules": {
        "zh": "处理项",
        "en": "Rules",
    },
    "polish.rule_tables": {
        "zh": "表格转述",
        "en": "Tables to speech",
    },
    "polish.rule_numbers": {
        "zh": "数字口语化",
        "en": "Speakable numbers",
    },
    "polish.rule_cleanup": {
        "zh": "排版与符号清理",
        "en": "Cleanup markup",
    },
    "polish.start": {
        "zh": "开始润色",
        "en": "Start Polishing",
    },
    "polish.polishing": {
        "zh": "正在润色...",
        "en": "Polishing...",
    },
    "polish.progress": {
        "zh": "润色进度",
        "en": "Polishing Progress",
    },
    "polish.log": {
        "zh": "润色日志",
        "en": "Polishing Log",
    },
    "polish.preview": {
        "zh": "预览",
        "en": "Preview",
    },
    "polish.original": {
        "zh": "原文",
        "en": "Original",
    },
    "polish.polished": {
        "zh": "润色后",
        "en": "Polished",
    },
    "polish.no_preview": {
        "zh": "点击左侧章节查看预览",
        "en": "Click a chapter on the left to preview",
    },
    "polish.export": {
        "zh": "导出润色文本",
        "en": "Export Polished Text",
    },
    "polish.export_success": {
        "zh": "润色文本已导出",
        "en": "Polished text exported",
    },
    "polish.no_polished": {
        "zh": "暂无可导出的润色结果，请先润色",
        "en": "No polished text to export yet — polish first",
    },
    "polish.next": {
        "zh": "下一步：生成 JSON",
        "en": "Next: Generate JSON",
    },
    "polish.success": {
        "zh": "润色完成",
        "en": "Polishing Complete",
    },
    "polish.error": {
        "zh": "润色失败",
        "en": "Polishing Failed",
    },
    "polish.no_chapters": {
        "zh": "没有可用的章节",
        "en": "No chapters available",
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
    "speaker.prompt_audio": {
        "zh": "提示音频",
        "en": "Prompt Audio",
    },
    "speaker.browse": {
        "zh": "浏览",
        "en": "Browse",
    },
    "speaker.synthesize": {
        "zh": "语音合成",
        "en": "Synthesize Audio",
    },
    "speaker.no_prompt_audio": {
        "zh": "请至少设置一个分类的提示音频",
        "en": "Please set prompt audio for at least one category",
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
    "settings.tts": {
        "zh": "TTS 语音合成",
        "en": "TTS Synthesis",
    },
    "settings.tts_server_url": {
        "zh": "TTS 服务地址",
        "en": "TTS Server URL",
    },
    "settings.prompts": {
        "zh": "LLM 提示词",
        "en": "LLM Prompts",
    },
    "settings.prompt_hint": {
        "zh": "留空则使用内置默认。可用占位符：{text}（待处理文本）、{rules}（润色规则）、{speaker_list}（人物列表）。修改前请谨慎，可能影响输出结构。",
        "en": "Leave empty to use the built-in default. Placeholders: {text}, {rules}, {speaker_list}. Edit with care — changes may affect output structure.",
    },
    "settings.prompt_json_gen": {
        "zh": "JSON 生成提示词",
        "en": "JSON Generation Prompt",
    },
    "settings.prompt_polish": {
        "zh": "润色提示词",
        "en": "Polish Prompt",
    },
    "settings.prompt_polish_rules": {
        "zh": "润色规则（对应润色页的勾选项）",
        "en": "Polish Rules (match the polish page checkboxes)",
    },
    "settings.prompt_rule_tables": {
        "zh": "表格转述",
        "en": "Tables to speech",
    },
    "settings.prompt_rule_numbers": {
        "zh": "数字口语化",
        "en": "Speakable numbers",
    },
    "settings.prompt_rule_cleanup": {
        "zh": "排版与符号清理",
        "en": "Cleanup markup",
    },
    "settings.prompt_classify": {
        "zh": "说话人分类提示词",
        "en": "Speaker Classification Prompt",
    },
    "settings.restore_default": {
        "zh": "恢复默认",
        "en": "Restore Default",
    },

    # ==================================================================
    # TTS page
    # ==================================================================
    "tts.title": {
        "zh": "语音合成",
        "en": "TTS Synthesis",
    },
    "tts.output_dir": {
        "zh": "输出目录",
        "en": "Output Directory",
    },
    "tts.select_dir": {
        "zh": "选择目录",
        "en": "Select Directory",
    },
    "tts.select_all": {
        "zh": "全选",
        "en": "Select All",
    },
    "tts.deselect_all": {
        "zh": "取消全选",
        "en": "Deselect All",
    },
    "tts.start": {
        "zh": "开始合成",
        "en": "Start Synthesis",
    },
    "tts.cancel": {
        "zh": "取消合成",
        "en": "Cancel",
    },
    "tts.progress": {
        "zh": "合成进度",
        "en": "Synthesis Progress",
    },
    "tts.log": {
        "zh": "合成日志",
        "en": "Synthesis Log",
    },
    "tts.chapter_status": {
        "zh": "章节状态",
        "en": "Chapter Status",
    },
    "tts.no_chapters": {
        "zh": "没有可用的章节",
        "en": "No chapters available",
    },
    "tts.no_output_dir": {
        "zh": "请先选择输出目录",
        "en": "Please select an output directory first",
    },
    "tts.synthesizing": {
        "zh": "正在合成...",
        "en": "Synthesizing...",
    },
    "tts.success": {
        "zh": "合成完成",
        "en": "Synthesis Complete",
    },
    "tts.error": {
        "zh": "合成失败",
        "en": "Synthesis Failed",
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
