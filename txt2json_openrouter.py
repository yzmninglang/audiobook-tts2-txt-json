# -*- coding: utf-8 -*-
"""
使用 OpenRouter API 将 人性的弱点_chapters 目录下的所有 .txt 文件并行转换为 index-tts v2 有声书 JSON，并保存为对应的 .json 文件
依赖:
  pip install openai

环境变量或配置:
  OPENROUTER_API_KEY=你的OpenRouter API密钥

代理:
  本脚本会自动设置 HTTP(S)_PROXY = http://127.0.0.1:7892
"""

import os
import json
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
import config

# ========== 基本配置 ==========
# 代理（按需注释掉）
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7892"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7892"

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

# ========== 生成配置 ==========
# 使用 OpenAI 兼容接口，默认参数

# ========== 读取原文 ==========
def process_single_file(txt_path):
    """处理单个TXT文件，转换为JSON"""
    print(f"开始处理: {txt_path}")
    text = txt_path.read_text(encoding="utf-8")

    # 构造最终提示
    user_prompt = (
        "你是一个严格的格式化器。"
        "根据下述【规范】将【原文】转换为 index-tts v2 有声书 JSON，必须只输出有效 JSON 数组，不要任何额外说明：\n"
        "【规范】如下：\n" + SPEC_PROMPT + "\n"
        "【原文】如下：\n" + text + "\n"
        "请确保输出是纯净的JSON数组格式。"
    )

    # 调用生成
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=4096,  # 根据需要调整
        )
        raw = response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"API 调用失败: {e}")

    # 兜底：确保拿到合法 JSON
    def extract_json(s: str):
        try:
            return json.loads(s)
        except Exception:
            pass
        m = re.search(r"(\[.*\]|\{.*\})", s, flags=re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                return None
        return None

    data = extract_json(raw)
    if not isinstance(data, list):
        raise ValueError(f"模型未返回预期的 JSON 数组，请检查 {txt_path} 或重试。")

    # 可选：轻度校验
    def minimally_valid(item):
        return (
            isinstance(item, dict)
            and set(item.keys()) == {"speaker", "content", "emo_vector", "delay"}
            and isinstance(item["speaker"], str)
            and isinstance(item["content"], str)
            and isinstance(item["emo_vector"], list)
            and len(item["emo_vector"]) == 8
            and all(isinstance(x, (int, float)) for x in item["emo_vector"])
            and isinstance(item["delay"], int)
        )

    if not all(minimally_valid(x) for x in data):
        print(f"警告：{txt_path} 部分项不完全符合字段/类型要求，请检查结果。")

    # 保存结果
    json_path = txt_path.with_suffix('.json')
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已保存到 {json_path}")
    return json_path

# ========== 任务提示词（你的规范，原样内嵌） ==========
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
三、内容处理与技术要求
长段落拆分:
任何超过100个字的段落必须被拆分。
拆分点应在自然的停顿处（如句号、逗号后），确保每段在80-100字以内。
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
模板示例 (已按最终版新规修订)
JSON
[
  {
    "speaker": "旁白",
    "content": "夜色如墨，冷雨敲打着窗棂，房间里唯一的光源来自桌上那盏昏黄的台灯。",
    "emo_vector": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "delay": 800
  },
  {
    "speaker": "李昂",
    "content": "他们...真的都走了吗？",
    "emo_vector": [0.0, 0.0, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0],
    "delay": 1200
  },
  {
    "speaker": "旁白",
    "content": "他的声音在空旷的房间里显得格外沙哑和无力，仿佛每一个字都耗尽了全身的力气。",
    "emo_vector": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "delay": 700
  },
  {
    "speaker": "神秘人",
    "content": "别担心，我们很快就会再见面的。",
    "emo_vector": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "delay": 900
  }
]
"""

# ========== 主函数：并行处理目录下的所有TXT文件 ==========
def main():
    chapters_dir = Path("./人性的弱点_chapters")
    if not chapters_dir.exists() or not chapters_dir.is_dir():
        raise FileNotFoundError("未找到 ./人性的弱点_chapters 目录，请确保拆分后的文件在此目录下。")

    txt_files = list(chapters_dir.glob("*.txt"))
    if not txt_files:
        raise FileNotFoundError("在 ./人性的弱点_chapters 目录下未找到任何 .txt 文件。")

    # 过滤出没有对应JSON文件的TXT文件
    files_to_process = []
    for txt_path in txt_files:
        json_path = txt_path.with_suffix('.json')
        if not json_path.exists():
            files_to_process.append(txt_path)
        else:
            print(f"跳过: {txt_path} (已存在对应的JSON文件)")

    if not files_to_process:
        print("所有TXT文件都已处理完毕，无需再次转换。")
        return

    print(f"找到 {len(files_to_process)} 个需要处理的TXT文件，开始并行处理...")

    # 使用线程池并行处理
    max_workers = getattr(config, 'max_workers', 6)  # 默认6个并发，避免API限制
    with ThreadPoolExecutor(max_workers=min(len(files_to_process), max_workers)) as executor:
        futures = [executor.submit(process_single_file, txt_path) for txt_path in files_to_process]

        for future in as_completed(futures):
            try:
                result = future.result()
                print(f"完成: {result}")
            except Exception as e:
                print(f"处理失败: {e}")

    print("所有文件处理完成！")

if __name__ == "__main__":
    main()