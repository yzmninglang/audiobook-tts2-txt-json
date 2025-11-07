# 人性的弱点 有声书转换工具

这是一个用于处理《人性的弱点》文本文件并转换为 index-tts v2 有声书 JSON 格式的工具集。

## 功能概述

- `split_txt.py`: 将完整的文本文件按章节分割成多个独立的文件
- `txt2json.py`: 使用 Google Gemini API 将分割后的章节文件转换为有声书 JSON 格式
- `txt2json_openrouter.py`: 使用 OpenRouter API 将分割后的章节文件转换为有声书 JSON 格式（支持多线程和多种提供商）

## 依赖

- Python 3.6+
- `google-generativeai` 库（用于 txt2json.py）
- `openai` 库（用于 txt2json_openrouter.py）
- Google Gemini API 密钥（用于 txt2json.py）
- OpenRouter API 密钥（用于 txt2json_openrouter.py）

## 安装

1. 安装依赖：
   ```bash
   pip install google-generativeai openai
   ```

2. 配置 API 密钥：
   编辑 `config.py` 文件：
   - 对于 `txt2json.py`：设置 `api_key` 为你的 Google Gemini API 密钥
   - 对于 `txt2json_openrouter.py`：设置 `openrouter_api_key`、`openrouter_base_url` 和 `openrouter_model`
   ```python
   # Gemini 配置
   api_key = "你的Gemini API密钥"

   # OpenRouter 配置
   openrouter_api_key = "你的OpenRouter API密钥"
   openrouter_base_url = "https://openrouter.ai/api/v1"
   openrouter_model = "openai/gpt-4o-mini"  # 或其他支持的模型
   ```

## 使用步骤

### 1. 准备原始文本文件

确保工作目录下有 `人性的弱点.txt` 文件。

### 2. 分割文本文件

运行 `split_txt.py` 来按章节分割文本：

```bash
python split_txt.py
```

此脚本将：
- 读取 `人性的弱点.txt` 文件
- 使用正则表达式匹配章节标题（格式：第xxx篇）
- 创建 `人性的弱点_chapters` 目录
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

## 故障排除

- 如果未找到章节切分点，检查文本格式是否符合 "第xxx篇" 模式
- 如果 API 调用失败，检查密钥配置和网络代理设置
- 如果 JSON 格式错误，脚本会尝试提取有效 JSON，但建议检查原文内容