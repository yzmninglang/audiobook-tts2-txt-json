# -*- coding: utf-8 -*-
"""
Core algorithms extracted from CLI scripts as pure functions.
No file I/O, no global state.
"""

from __future__ import annotations

import json
import re
from fuzzywuzzy import fuzz


# ============================================================
# SPEC_PROMPT  (verbatim from txt2json_openrouter.py)
# ============================================================
SPEC_PROMPT = r"""
请将提供的小说文本转换为专门用于 index-tts v2 引擎的有声书JSON格式。必须严格遵循以下所有规范和原则。
核心概念：情感向量 (emo_vector)
此引擎使用一个包含8个浮点数的数组来精确控制情感。
向量顺序（固定）: [喜, 怒, 哀, 惧, 厌恶, 低落, 惊喜, 平静]
核心原则: 默认情感为 完全中性 [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]。只在绝对必要时，才对情感向量进行微调。
数值上限: 任何单个情感权重值不得超过 0.3。
一、输出格式与字段规范
总格式: 输出必须是一个有效的JSON数组 [...]。
对象字段: 每个对象必须且只能包含以下四个字段：
speaker: 字符串，说话者姓名 (如 "旁白", "角色名")。
content: 字符串，对话或旁白内容。
emo_vector: 数组，包含8个浮点数。
delay: 整数，该语音结束后的停顿时间（毫秒）。
二、情感向量 (emo_vector) 赋值核心原则
原则: 旁白必须是完全中性的讲述者，不携带任何情感、氛围或倾向。
赋值方法: 固定且唯一地使用零向量。
标准值: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
原则: 以"零向量"为基准，遵循"非必要，不调整"的极简主义。情感赋值必须基于深度的上下文分析（黄金标准），但表现形式上必须极度克制。
赋值方法:
默认状态: 角色的 emo_vector 默认为 [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]。
调整前提: 只有当角色的情绪通过上下文（如角色关系、处境、对话目的等）表现出明确且必要的情感倾向时，才进行调整。
调整方式:
优先单一情感: 尽量只调整一个最核心的情感值（例如，表达悲伤时只调整"哀"）。
审慎组合: 仅在角色情感确实是复杂交织（如讽刺、强颜欢笑）且不可用单一情感表达时，才组合两个情感值。
保持轻微: 所有调整值必须是轻情绪，最大值为 0.3。

标准值: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1] （略带平静的客观叙述）
特殊情况: 悬念铺垫或气氛营造时可调整为 [0.0, 0.0, 0.0, 0.1, 0.0, 0.0, 0.1, 0.0] （略带紧张和惊喜）
演绎角色对话（模拟人物说话）：
根据角色情绪进行调整，但保持克制

范例：
悲伤角色: [0.0, 0.0, 0.3, 0.0, 0.0, 0.1, 0.0, 0.0]
愤怒角色: [0.0, 0.3, 0.0, 0.0, 0.1, 0.0, 0.0, 0.0]
喜悦角色: [0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0]
平淡对话: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1]
闲白评论（说书人跳出剧情的评论、感慨、调侃）：
幽默调侃: [0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0]
感慨评价: [0.0, 0.0, 0.1, 0.0, 0.0, 0.1, 0.0, 0.1]
讥讽批评: [0.0, 0.1, 0.0, 0.0, 0.2, 0.0, 0.0, 0.0]
包袱铺垫与抖响：
铺垫阶段: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.0] （带点悬念）
抖包袱: [0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.0] （轻松愉快带惊喜）

三、内容处理与技术要求
长段落拆分:
任何超过80个字的段落必须被拆分。
拆分点应在自然的停顿处（如句号、逗号后），确保每段在60-80字以内。
重要: 由同一个长段落拆分出的所有片段，其 speaker 和 emo_vector 必须完全相同。
内容与标点:
content 字段中只保留 ，、、、。、！、？ 和 ... 这几种标点符号。
原文中的所有英文引号 " 必须在JSON中转义为 \"。
停顿 (delay):
旁白 delay 通常在 300-800ms。
角色对话 delay 通常在 400-1500ms。
在情感转折、关键信息揭示或戏剧性停顿处，应设置更长的 delay 值（例如 1200ms 以上）。
格式纯洁性:
不要添加任何规定之外的字段或注释。输出必须是纯净、可被程序直接解析的JSON。
不需要返回markdown代码块语法如```json  ```
模板示例 (已按最终版新规修订)
CODE
JSON
[
  {
    "speaker": "旁白",
    "content": "夜色如墨，冷雨敲打着窗棂，房间里唯一的光源来自桌上那盏昏黄的台灯。",
    "emo_vector": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "delay": 800
  }
]
"""


# ============================================================
# Prompt templates & rendering
#
# Every LLM prompt is a *template*: runtime content is injected by
# replacing `{name}` placeholders.  We deliberately avoid str.format()
# because prompt bodies contain literal `{` / `}` (JSON examples).
# Each template has a built-in default below; users may override any of
# them via the settings page (persisted as `prompt_*` in config.yaml).
# ============================================================
def _fill(template: str, mapping: dict[str, str]) -> str:
    """Replace ``{key}`` occurrences in *template* with the mapped values.

    Only the named keys are replaced — other braces are left untouched.
    """
    out = template
    for key, value in mapping.items():
        out = out.replace("{" + key + "}", value)
    return out


# Default JSON-generation prompt.  ``{text}`` is the novel fragment.
DEFAULT_JSON_GEN_PROMPT = (
    "你是一个严格的格式化器。\n"
    "根据下述【规范】将提供的【小说片段】转换为 index-tts v2 有声书 JSON。\n"
    "注意：这只是小说的一小部分，请只处理这段文字，不要编造开头或结尾，直接输出 JSON 数组。\n\n"
    "【规范】如下：\n" + SPEC_PROMPT + "\n"
    "【小说片段】如下：\n'''\n{text}\n'''\n\n"
    "请直接输出 JSON 数组："
)


def build_json_gen_prompt(chunk_text: str, template: str | None = None) -> str:
    """Build the LLM prompt that turns one text chunk into JSON entries.

    Parameters
    ----------
    chunk_text : str
        The novel fragment to convert.
    template : str or None
        Override template.  When *None*, :data:`DEFAULT_JSON_GEN_PROMPT`
        is used.  If the template lacks a ``{text}`` placeholder the
        fragment is appended at the end.
    """
    tpl = template or DEFAULT_JSON_GEN_PROMPT
    if "{text}" not in tpl:
        tpl = tpl.rstrip() + "\n\n'''\n{text}\n'''"
    return _fill(tpl, {"text": chunk_text})


# ============================================================
# split_by_fuzzy_matching  (ported from split_chaps.py)
# ============================================================
def split_by_fuzzy_matching(
    text_lines: list[str],
    chapter_titles: list[str],
    threshold: int = 40,
) -> list[dict]:
    """Split book text into chapters using fuzzy title matching.

    Parameters
    ----------
    text_lines : list[str]
        Raw lines of the book (already read from file).
    chapter_titles : list[str]
        List of chapter title strings.
    threshold : int, optional
        Fuzzy match threshold (default 40).

    Returns
    -------
    list[dict]
        Each dict has keys: index (1-based), title (str), content (str),
        line_start (int), line_end (int).
    """
    # -- 1. Collect potential split points: title -> [(line_index, score)] --
    split_points: dict[str, list[tuple[int, int]]] = {
        title: [] for title in chapter_titles
    }

    for idx, raw_line in enumerate(text_lines):
        line = raw_line.strip()
        if not line:
            continue

        best_match_score = 0
        best_match_title = ""

        for title in chapter_titles:
            score = fuzz.ratio(line, title)
            if score > best_match_score:
                best_match_score = score
                best_match_title = title

        # 2. If best score >= threshold, record as potential split
        if best_match_score >= threshold:
            split_points[best_match_title].append((idx, best_match_score))

    # -- 3. For each title, pick the point with highest score --
    final_split_points: list[tuple[int, str]] = []
    for title, points in split_points.items():
        if points:
            best_point = max(points, key=lambda x: x[1])
            final_split_points.append((best_point[0], title))

    # -- 4. Sort split points by line number --
    final_split_points.sort(key=lambda x: x[0])

    # -- 5. Walk through lines, splitting at each split point --
    chapters: list[dict] = []
    current_chapter_lines: list[str] = []
    current_chapter_title = "扉页"
    chapter_num = 1
    line_start = 0

    split_idx = 0
    for idx, raw_line in enumerate(text_lines):
        line = raw_line.strip()
        if not line:
            continue

        if (
            split_idx < len(final_split_points)
            and idx == final_split_points[split_idx][0]
        ):
            # Save current chapter
            if current_chapter_lines:
                chapters.append({
                    "index": chapter_num,
                    "title": current_chapter_title,
                    "content": "\n".join(current_chapter_lines),
                    "line_start": line_start,
                    "line_end": idx - 1,
                })
                current_chapter_lines = []

            # Start new chapter
            current_chapter_title = final_split_points[split_idx][1]
            line_start = idx
            current_chapter_lines.append(line)
            chapter_num += 1
            split_idx += 1
        else:
            current_chapter_lines.append(line)

    # -- Handle the last chapter --
    if current_chapter_lines:
        chapters.append({
            "index": chapter_num,
            "title": current_chapter_title,
            "content": "\n".join(current_chapter_lines),
            "line_start": line_start,
            "line_end": len(text_lines) - 1,
        })

    return chapters


# ============================================================
# split_text_into_chunks  (from txt2json_openrouter.py)
# ============================================================
def split_text_into_chunks(text: str, max_size: int = 8000) -> list[str]:
    """Split *text* by sentence boundaries and group into chunks under
    *max_size* characters.

    Sentence boundaries are: 。！？!?\\n
    """
    sentences = re.split(r'([。！？!?\n]+)', text)

    chunks: list[str] = []
    current_chunk = ""

    for i in range(0, len(sentences), 2):
        sentence_text = sentences[i]
        punctuation = sentences[i + 1] if i + 1 < len(sentences) else ""
        full_sentence = sentence_text + punctuation

        if len(current_chunk) + len(full_sentence) > max_size:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = full_sentence
        else:
            current_chunk += full_sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


# ============================================================
# extract_json_from_response  (from txt2json_openrouter.py)
# ============================================================
def extract_json_from_response(content: str) -> list | None:
    """Try to parse a JSON array from an LLM response string.

    First attempts ``json.loads(content)``; on failure falls back to a
    regex search for a ``[...]`` pattern.
    """
    try:
        return json.loads(content)
    except Exception:
        pass

    m = re.search(r"(\[.*\])", content, flags=re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return None


# ============================================================
# extract_chapter_title  (from txt2json_openrouter.py)
# ============================================================
def extract_chapter_title(filename: str) -> str | None:
    """Extract a chapter title from a filename like ``P02_Title.txt``.

    Returns a string such as ``"第2章 Title"`` or *None* if the pattern
    does not match.
    """
    name = filename.rsplit('.', 1)[0]
    parts = name.split('_', 1)
    if len(parts) == 2:
        p_part, title_part = parts
        if p_part.startswith('P') and p_part[1:].isdigit():
            num = int(p_part[1:])
            return f"第{num}章 {title_part}"
    return None


# ============================================================
# extract_speakers_from_entries  (ported from extract_speakers.py)
# ============================================================
def extract_speakers_from_entries(
    all_entries: list[list[dict]],
) -> list[tuple[str, int]]:
    """Extract unique speaker names and their counts from in-memory data.

    Parameters
    ----------
    all_entries : list[list[dict]]
        A list of chapter entry lists.  Each entry dict is expected to
        have a ``"speaker"`` key.

    Returns
    -------
    list[tuple[str, int]]
        ``(name, count)`` tuples sorted by count descending.
    """
    speakers: dict[str, int] = {}

    for chapter_entries in all_entries:
        if not isinstance(chapter_entries, list):
            continue
        for item in chapter_entries:
            if isinstance(item, dict) and "speaker" in item:
                speaker = item["speaker"].strip()
                if speaker:
                    speakers[speaker] = speakers.get(speaker, 0) + 1

    return sorted(speakers.items(), key=lambda x: x[1], reverse=True)


# ============================================================
# build_speaker_mapping  (from replace_speakers.py)
# ============================================================
def build_speaker_mapping(classifications: dict[str, list[str]]) -> dict[str, str]:
    """Build a ``{name: category}`` mapping from a classification dict.

    Parameters
    ----------
    classifications : dict[str, list[str]]
        ``{category: [speaker_name, ...]}`` as returned by the AI
        classification step.

    Returns
    -------
    dict[str, str]
        ``{speaker_name: category}``
    """
    mapping: dict[str, str] = {}
    for category, speakers in classifications.items():
        for speaker in speakers:
            mapping[speaker] = category
    return mapping


# ============================================================
# apply_speaker_replacements  (from replace_speakers.py)
# ============================================================
def apply_speaker_replacements(
    entries: list[dict],
    mapping: dict[str, str],
) -> list[dict]:
    """Replace speaker names in *entries* according to *mapping*.

    Modifies the dicts **in-place** and returns the same list for
    convenience.
    """
    for item in entries:
        if isinstance(item, dict) and "speaker" in item:
            original_speaker = item["speaker"]
            if original_speaker in mapping:
                item["speaker"] = mapping[original_speaker]
    return entries


# ============================================================
# build_classify_prompt  (from extract_speakers.py)
# ============================================================
DEFAULT_CLASSIFY_PROMPT = """请分析以下人物名称列表，根据中文语境和常见认知，将每个人物分类为以下六类之一：

分类标准：
- 年龄：少（青少年/年轻人）、中（中年人）、老（老年人）
- 性别：男、女

六类组合：少男、少女、中男、中女、老男、老女

请以严格的JSON格式返回结果，格式如下：
{
  "少男": ["人物1", "人物2"],
  "少女": ["人物3", "人物4"],
  "中男": ["人物5", "人物6"],
  "中女": ["人物7", "人物8"],
  "老男": ["人物9", "人物10"],
  "老女": ["人物11", "人物12"]
}

注意：
1. 每个类别都是数组，即使为空数组也要包含
2. 所有人物都必须被分类到恰好一个类别中
3. 基于人物名称的常见印象进行合理推断
4. 如果不确定，优先选择"中男"或"中女"
5. 不需要返回markdown代码块语法如```json  ```

人物列表：
{speaker_list}

请返回纯净的JSON格式，不要任何额外说明。"""


def build_classify_prompt(
    speaker_names: list[str],
    template: str | None = None,
) -> str:
    """Build the LLM prompt for classifying speaker names.

    Parameters
    ----------
    speaker_names : list[str]
        Speaker names **excluding** "旁白".
    template : str or None
        Override template.  When *None*, :data:`DEFAULT_CLASSIFY_PROMPT`
        is used.  If the template lacks a ``{speaker_list}`` placeholder
        the name list is appended at the end.

    Returns
    -------
    str
        The full prompt string ready to send to an LLM.
    """
    speaker_list = "\n".join(f"- {s}" for s in speaker_names)
    tpl = template or DEFAULT_CLASSIFY_PROMPT
    if "{speaker_list}" not in tpl:
        tpl = tpl.rstrip() + "\n\n人物列表：\n{speaker_list}"
    return _fill(tpl, {"speaker_list": speaker_list})


# ============================================================
# Text polishing (前置润色) — listening adaptation for audiobooks
# ============================================================
POLISH_BASE_PROMPT = r"""
你是一位有声书文本预处理编辑。你的任务是把电子书文本改写为"适合朗读、适合听"的口播稿，
为后续的 TTS 语音合成做准备。

【最高原则】
1. 忠实原文：绝不增删、概括或曲解文章的主要内容和观点，只做"听感适配"。
2. 保持原有的段落顺序、人称、时态与语言风格不变。
3. 遇到无法确定的内容，保持原文，不要臆造。
4. 只输出处理后的正文本身，不要任何解释、标题或 markdown 代码块。
"""

# Selectable rule blocks, keyed by an id the UI can toggle.
POLISH_RULES: dict[str, str] = {
    "tables": r"""【表格转述】
把表格（包括 markdown 表格，如 | 名称 | 数值 |）改写成连贯、听得懂的口语化句子：
- 按"表头＋数值"的顺序逐项念出，必要时用连接词串联。例如：
  | 年份 | 收入 |
  | 2020 | 100  |
  | 2021 | 150  |
  改写为："2020年，收入是一百；2021年，收入是一百五十。"
- 表头较长时，先用一句话概括"下面是关于……的表格"，再逐项念出。
- 空单元格直接忽略；不要念出竖线、横线等表格符号。""",
    "numbers": r"""【数字与单位口语化】
把只适合阅读、不适合朗读的写法改写为适合朗读的中文口语，含义保持不变：
- 年份：1998年 → 一九九八年；2010年 → 二零一零年
- 百分比：35% → 百分之三十五；2.5% → 百分之二点五
- 分数：3/4 → 四分之三
- 小数：3.1415 → 三点一四一五
- 时间：10:30 → 十点三十分
- 金额与大数：12,000 → 一万二千；$1,200 → 一千二百美元（保留原币种）
- 区间：5-10 → 五到十；1990—1999 → 一九九零年到一九九九年
- 序号编号：第2章 → 第二章；A. → 第一；II → 第二
- 专业符号按中文习惯念出：H₂O → 水，CO₂ → 二氧化碳，α → 阿尔法，
  β → 贝塔，°C → 摄氏度，km → 公里
- 不确定含义的缩写、代号、编号，保持原样。""",
    "cleanup": r"""【排版与符号清理】
删除或改写无法朗读、干扰收听的排版元素，同时保留正文文字：
- 去掉 markdown 标记：# 标题号、** 加粗、* 斜体、` 反引号、``` 代码围栏、- 与 1. 等列表符号
- 无序列表（- 项目）改成"第一，……；第二，……"或自然连接的句子
- 删除纯图片占位符、图注编号、页码、页眉页脚、脚注标记、参考文献编号
- "如图3-1所示""见下表"等指向性文字，保留文字本身
- 网址、邮箱、文件路径：若只是标注来源，简化为"相关链接"；若必须念出，按字符念
- 删除乱码、控制字符、多余空格与重复空行，保留中文标点（，。！？、；：""''——《》）""",
}

POLISH_OUTPUT_RULES = r"""
【输出要求】
- 只输出可直接朗读的正文，段落之间用一个换行分隔。
- 不要输出 JSON，不要输出 markdown 代码块，不要输出任何解释或前后缀。
- 若某段文字无需修改，原样返回。
"""

# Default polish template.  ``{rules}`` expands to the enabled rule blocks,
# ``{text}`` to the fragment being polished.
DEFAULT_POLISH_PROMPT = (
    "请根据下述【润色规范】，把【文本片段】改写为适合朗读的口播稿。\n"
    "注意：这只是全书的一小部分，请只处理给出的文字，不要编造开头或结尾。\n"
    "直接输出处理后的正文，不要任何解释。\n\n"
    "【润色规范】\n"
    + POLISH_BASE_PROMPT
    + "\n{rules}\n"
    + POLISH_OUTPUT_RULES
    + "\n【文本片段】\n'''\n{text}\n'''\n\n请输出处理后的正文："
)


def build_polish_prompt(
    chunk_text: str,
    rules: list[str] | None = None,
    template: str | None = None,
    rule_texts: dict[str, str] | None = None,
) -> str:
    """Build the LLM prompt for polishing one text chunk.

    Parameters
    ----------
    chunk_text : str
        The raw text fragment to polish.
    rules : list[str] or None
        Which rule blocks to enable.  When *None*, every rule is enabled.
    template : str or None
        Override template.  When *None*, :data:`DEFAULT_POLISH_PROMPT`
        is used.  If the template lacks a ``{text}`` placeholder the
        fragment is appended at the end.
    rule_texts : dict[str, str] or None
        Override text for individual rule blocks, keyed like
        :data:`POLISH_RULES`.  Empty values fall back to the built-in
        default for that rule.

    Returns
    -------
    str
        The full prompt string ready to send to an LLM.
    """
    if rules is None:
        rules = list(POLISH_RULES.keys())

    texts = dict(POLISH_RULES)
    if rule_texts:
        texts.update({k: v for k, v in rule_texts.items() if v})

    rule_text = "\n".join(texts[k] for k in rules if k in texts)

    tpl = template or DEFAULT_POLISH_PROMPT
    if "{text}" not in tpl:
        tpl = tpl.rstrip() + "\n\n'''\n{text}\n'''"
    return _fill(tpl, {"rules": rule_text, "text": chunk_text})


def clean_llm_text(raw: str) -> str:
    """Strip code fences and stray whitespace from an LLM plain-text reply."""
    if not raw:
        return ""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()
