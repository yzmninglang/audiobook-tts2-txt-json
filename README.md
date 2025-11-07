# 人性的弱点 有声书转换工具

这是一个用于处理《人性的弱点》文本文件并转换为 index-tts v2 有声书 JSON 格式的工具集。

## 功能概述

- `split_txt.py`: 将完整的文本文件按章节分割成多个独立的文件（适用于《人性的弱点》）
- `split_sophie.py`: 将《苏菲的世界》文本文件按章节分割成多个独立的文件
- `split_laozi.py`: 将《老子的逆袭人生》文本文件按 Markdown 一级标题（^# ）分割成多个独立的文件
- `split_psychology.py`: 将《分析心理学的理论与实践》文本文件按"第xxx讲"分割成多个独立的文件
- `txt2json.py`: 使用 Google Gemini API 将分割后的章节文件转换为有声书 JSON 格式
- `txt2json_openrouter.py`: 使用 OpenRouter API 将分割后的章节文件转换为有声书 JSON 格式（支持多线程和多种提供商）
- `txt2json_qwen.py`: 使用阿里 Qwen Long API 将分割后的章节文件转换为有声书 JSON 格式（支持多线程）
- `extract_speakers.py`: 从指定文件夹中的所有 JSON 文件中提取并打印所有唯一的 speaker 名称
- `replace_speakers.py`: 读取 speaker 分类文件，自动替换所有 JSON 文件中的 speaker 为对应的分类标签

## 依赖

- Python 3.6+
- `google-generativeai` 库（用于 txt2json.py）
- `openai` 库（用于 txt2json_openrouter.py 和 txt2json_qwen.py）
- Google Gemini API 密钥（用于 txt2json.py）
- OpenRouter API 密钥（用于 txt2json_openrouter.py）
- 阿里 Qwen API 密钥（用于 txt2json_qwen.py）

## 安装

1. 安装依赖：
   ```bash
   pip install google-generativeai openai
   ```

2. 配置 API 密钥和输入目录：
   编辑 `config.py` 文件：
   - 设置 `input_dir` 为你的小说章节目录路径（默认为 "./人性的弱点_chapters"）
   - 对于 `txt2json.py`：设置 `api_key` 为你的 Google Gemini API 密钥
   - 对于 `txt2json_openrouter.py`：设置 `openrouter_api_key`、`openrouter_base_url` 和 `openrouter_model`
   - 对于 `txt2json_qwen.py`：设置 `qwen_api_key`、`qwen_base_url` 和 `qwen_model`
   ```python
   # 输入目录配置
   input_dir = "./人性的弱点_chapters"  # 修改为你的小说章节目录

   # Gemini 配置
   api_key = "你的Gemini API密钥"

   # OpenRouter 配置
   openrouter_api_key = "你的OpenRouter API密钥"
   openrouter_base_url = "https://openrouter.ai/api/v1"
   openrouter_model = "openai/gpt-4o-mini"  # 或其他支持的模型

   # 阿里 Qwen 配置
   qwen_api_key = "你的Qwen API密钥"
   qwen_base_url = "https://dashscope.aliyuncs.com/api/v1"
   qwen_model = "qwen-long"
   ```

## 使用步骤

### 1. 准备原始文本文件

确保工作目录下有原始文本文件（如 `人性的弱点.txt` 或 `苏菲的世界.txt`）。

### 2. 分割文本文件

根据不同的书籍选择相应的分割脚本：

#### 分割《人性的弱点》

运行 `split_txt.py` 来按章节分割文本：

```bash
python split_txt.py
```

此脚本将：
- 读取 `人性的弱点.txt` 文件
- 使用正则表达式匹配章节标题（格式：第xxx篇）
- 创建 `人性的弱点_chapters` 目录
- 将每个章节保存为单独的 `.txt` 文件

#### 分割《苏菲的世界》

运行 `split_sophie.py` 来按章节分割文本：

```bash
python split_sophie.py
```

此脚本将：
- 读取 `苏菲的世界.txt` 文件
- 根据提供的章节标题列表进行匹配
- 创建 `苏菲的世界_chapters` 目录
- 将每个章节保存为单独的 `.txt` 文件

#### 分割《老子的逆袭人生》

运行 `split_laozi.py` 来按 Markdown 一级标题分割文本：

```bash
python split_laozi.py
```

此脚本将：
- 读取 `老子的逆袭人生.txt` 文件
- 使用正则表达式匹配 Markdown 一级标题（^# ）
- 创建 `老子的逆袭人生_chapters` 目录
- 将每个一级标题下的内容保存为单独的 `.txt` 文件

#### 分割《分析心理学的理论与实践》

运行 `split_psychology.py` 来按章节分割文本：

```bash
python split_psychology.py
```

此脚本将：
- 读取 `分析心理学的理论与实践.txt` 文件
- 使用正则表达式匹配章节标题（格式：第xxx讲）
- 创建 `分析心理学的理论与实践_chapters` 目录
- 将每个章节保存为单独的 `.txt` 文件

### 3. 转换为 JSON 格式

选择以下任一脚本将分割后的章节转换为有声书 JSON：

#### 使用 Google Gemini API

运行 `txt2json.py`：

```bash
python txt2json.py
```

此脚本将：
- 扫描 `人性的弱点_chapters` 目录下的所有 `.txt` 文件
- 使用 Google Gemini 2.5 Pro 模型并行处理每个文件
- 为每个章节生成对应的 `.json` 文件
- 跳过已存在 JSON 文件的章节

#### 使用 OpenRouter API

运行 `txt2json_openrouter.py`：

```bash
python txt2json_openrouter.py
```

此脚本将：
- 扫描 `人性的弱点_chapters` 目录下的所有 `.txt` 文件
- 使用 OpenRouter API 并行处理每个文件（支持多种提供商）
- 为每个章节生成对应的 `.json` 文件
- 跳过已存在 JSON 文件的章节
- 支持多线程处理（可通过 `config.py` 中的 `max_workers` 配置并发数）

#### 使用阿里 Qwen Long API

运行 `txt2json_qwen.py`：

```bash
python txt2json_qwen.py
```

此脚本将：
- 扫描 `人性的弱点_chapters` 目录下的所有 `.txt` 文件
- 使用阿里 Qwen Long API 并行处理每个文件
- 为每个章节生成对应的 `.json` 文件
- 跳过已存在 JSON 文件的章节
- 支持多线程处理（可通过 `config.py` 中的 `max_workers` 配置并发数）
- 支持更长的上下文（max_tokens 设置为 32768）

## 配置说明

### API 配置

#### Google Gemini 配置
- API 密钥存储在 `config.py` 中的 `api_key`
- 默认使用代理 `http://127.0.0.1:7892`（如不需要可注释掉相关行）
- 模型：`gemini-2.5-pro`
- 生成参数：温度 0.2

#### OpenRouter 配置
- API 密钥存储在 `config.py` 中的 `openrouter_api_key`
- Base URL：`openrouter_base_url`（默认 `https://openrouter.ai/api/v1`）
- 模型：`openrouter_model`（默认 `openai/gpt-4o-mini`，可选择其他支持的模型）
- 生成参数：温度 0.2，最大 token 4096
- 多线程：通过 `max_workers` 配置并发数（默认 6）

#### 阿里 Qwen 配置
- API 密钥存储在 `config.py` 中的 `qwen_api_key`
- Base URL：`qwen_base_url`（默认 `https://dashscope.aliyuncs.com/api/v1`，阿里官网）
- 模型：`qwen_model`（默认 `qwen-long`）
- 生成参数：温度 0.2，最大 token 32768（支持更长上下文）
- 多线程：通过 `max_workers` 配置并发数（默认 6）

### JSON 格式规范

每个 JSON 文件包含一个数组，每个元素为对象：

```json
{
  "speaker": "说话者名称（如 '旁白' 或角色名）",
  "content": "对话或旁白内容",
  "emo_vector": [喜, 怒, 哀, 惧, 厌恶, 低落, 惊喜, 平静],  // 8个浮点数，范围 0.0-0.3
  "delay": 停顿时间（毫秒）
}
```

### 处理规则

- 旁白使用零向量 `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]`
- 角色情感向量默认零向量，仅在必要时微调
- 长段落自动拆分为 80-100 字的片段
- 保留特定标点符号：，。！？...
- 英文引号转义为 \"

## 注意事项

- 确保网络连接正常，以便调用 Gemini API
- 处理大量文件时可能需要较长时间，脚本使用并行处理以提高效率
- 如果遇到 API 限制，可调整线程池大小（默认最多 6 个并发）
- 生成的 JSON 文件可直接用于 index-tts v2 引擎

## 工具脚本

### 提取和分类 Speaker 名称

运行 `extract_speakers.py` 来从文件夹中的所有 JSON 文件中提取 speaker 名称并进行 AI 分类：

```bash
python extract_speakers.py
```

此脚本将：
- 扫描指定文件夹中的所有 `.json` 文件
- 提取每个 JSON 数组中所有唯一的 `speaker` 字段值
- 按字母顺序排序并打印所有 speaker 名称
- 使用 OpenRouter API 对非"旁白"speaker进行年龄和性别分类
- 分类结果分为六类：少男、少女、中男、中女、老男、老女
- 显示每个类别的 speaker 列表和数量
- 将完整的分类结果保存为 JSON 文件（格式：`{folder_path}_speaker_classifications.json`）

默认处理 `人性的弱点_chapters` 文件夹，可修改脚本中的 `folder_path` 变量来处理其他文件夹。

### 替换 Speaker 标签

运行 `replace_speakers.py` 来自动替换 JSON 文件中的 speaker：

```bash
python replace_speakers.py
```

此脚本将：
- 读取 `人性的弱点_chapters_speaker_classifications.json` 分类文件
- 扫描 `人性的弱点_chapters` 文件夹中的所有 `.json` 文件
- 将每个 JSON 文件中的 speaker 名称替换为对应的分类标签（少男、少女、中男、中女、老男、老女）
- 保留 "旁白" 不变
- 自动备份原始文件为 `.backup` 后缀
- 显示替换统计信息

可修改脚本中的 `folder_path` 和 `classification_file` 变量来处理其他文件夹和分类文件。

## 故障排除

- 如果未找到章节切分点，检查文本格式是否符合 "第xxx篇" 模式
- 如果 API 调用失败，检查密钥配置和网络代理设置
- 如果 JSON 格式错误，脚本会尝试提取有效 JSON，但建议检查原文内容