import json
import os
import time
from pathlib import Path
from openai import OpenAI
import config

# ========== 基本配置 ==========
# 代理（按需注释掉）
# os.environ["HTTP_PROXY"] = "http://127.0.0.1:7892"
# os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7892"

# OpenRouter 配置
API_KEY = config.openrouter_api_key
BASE_URL = config.openrouter_base_url
MODEL_NAME = config.openrouter_model

if not API_KEY:
    raise RuntimeError("未检测到 OPENROUTER_API_KEY，请先在 config.py 中设置。")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)

def extract_speakers_from_folder(folder_path):
    """
    从指定文件夹中的所有 JSON 文件中提取 speaker 名称及其出现次数
    """
    speakers = {}

    # 遍历文件夹中的所有 JSON 文件
    for json_file in Path(folder_path).glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 确保数据是列表格式
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'speaker' in item:
                        speaker = item['speaker'].strip()
                        if speaker:  # 只添加非空 speaker
                            speakers[speaker] = speakers.get(speaker, 0) + 1

        except Exception as e:
            print(f"处理文件 {json_file} 时出错: {e}")

    # 按出现次数从多到少排序
    return sorted(speakers.items(), key=lambda x: x[1], reverse=True)

def classify_speakers_with_ai(speakers):
    """
    使用 OpenRouter API 对 speaker 进行年龄和性别分类
    """
    # 过滤掉"旁白"，speakers是列表元组形式，需要提取名字
    non_narration_speakers = [s[0] for s in speakers if s[0] != "旁白"]

    if not non_narration_speakers:
        return {}

    # 构造提示词
    speaker_list = "\n".join(f"- {s}" for s in non_narration_speakers)

    prompt = f"""请分析以下人物名称列表，根据中文语境和常见认知，将每个人物分类为以下六类之一：

分类标准：
- 年龄：少（青少年/年轻人）、中（中年人）、老（老年人）
- 性别：男、女

六类组合：少男、少女、中男、中女、老男、老女

请以严格的JSON格式返回结果，格式如下：
{{
  "少男": ["人物1", "人物2"],
  "少女": ["人物3", "人物4"],
  "中男": ["人物5", "人物6"],
  "中女": ["人物7", "人物8"],
  "老男": ["人物9", "人物10"],
  "老女": ["人物11", "人物12"]
}}

注意：
1. 每个类别都是数组，即使为空数组也要包含
2. 所有人物都必须被分类到恰好一个类别中
3. 基于人物名称的常见印象进行合理推断
4. 如果不确定，优先选择"中男"或"中女"
5. 不需要返回markdown代码块语法如```json  ```

人物列表：
{speaker_list}

请返回纯净的JSON格式，不要任何额外说明。"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 降低温度以获得更一致的结果
                max_tokens=600000,
            )
            raw = response.choices[0].message.content

            # 检查并移除 markdown 代码块标记
            if raw.strip().startswith("```json") and raw.strip().endswith("```"):
                raw = raw.strip()[len("```json"): -len("```")].strip()
            elif raw.strip().startswith("```") and raw.strip().endswith("```"):
                raw = raw.strip()[len("```"): -len("```")].strip()

            # 解析 JSON
            print(raw)
            result = json.loads(raw)
            return result

        except Exception as e:
            print(f"API 调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                print("无法获取 AI 分类结果，返回空分类")
                return {}

def main():
    # 示例：处理人性的弱点_chapters文件夹
    folder_path = config.json_book_name

    if not os.path.exists(folder_path):
        print(f"文件夹 {folder_path} 不存在")
        return

    speakers = extract_speakers_from_folder(folder_path)

    print(f"从 {folder_path} 中提取到的所有 speaker 名称及其出现次数（按次数从多到少排序）：")
    print("=" * 50)
    for speaker, count in speakers:
        print(f"- {speaker}: {count} 次")
    print("=" * 50)
    print(f"总共找到 {len(speakers)} 个不同的 speaker")

    # 使用 AI 进行分类
    print("\n正在使用 AI 分析 speaker 分类...")
    classifications = classify_speakers_with_ai(speakers)
    # classifications = None

    if classifications:
        print("\nAI 分类结果：")
        print("=" * 50)
        for category, names in classifications.items():
            if names:  # 只显示非空类别
                print(f"{category} ({len(names)}人):")
                for name in names:
                    print(f"  - {name}")
                print()

        # 保存分类结果到 JSON 文件
        output_file = f"{folder_path}_speaker_classifications.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "folder": folder_path,
                "total_speakers": len(speakers),
                "all_speakers": dict(speakers),
                "classifications": classifications,
                "classification_summary": {
                    category: len(names) for category, names in classifications.items()
                }
            }, f, ensure_ascii=False, indent=2)

        print(f"分类结果已保存到: {output_file}")
    else:
        print("无法获取 AI 分类结果")

if __name__ == "__main__":
    main()