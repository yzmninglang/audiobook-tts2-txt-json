# -*- coding: utf-8 -*-
"""
使用 OpenRouter API 将小说文本并行转换为 index-tts v2 有声书 JSON。
修改版：采用分块处理（Chunking）策略，彻底解决长文本截断导致的 JSON 解码失败问题。
"""

import os
import json
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
import config

# # ========== 基本配置 ==========
# 代理（按需注释掉）
# os.environ["HTTP_PROXY"] = "http://127.0.0.1:7899"
# os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7899"

# OpenRouter 配置
API_KEY = config.openrouter_api_key
BASE_URL = config.openrouter_base_url
MODEL_NAME = config.openrouter_model

# 核心参数：切片大小（字符数）
# 建议设置在 1200-1500 之间，留出足够的 Token 给 Output JSON
MAX_CHUNK_SIZE = 8000 

if not API_KEY:
    raise RuntimeError("未检测到 OPENROUTER_API_KEY，请先在 config.py 中设置。")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)

# ========== 工具函数：智能切分文本 ==========
def split_text_into_chunks(text, max_size=1500):
    """
    按标点符号智能切分长文本，防止截断句子。
    """
    # 正则：按换行、句号、问号、感叹号切分，并保留分隔符
    # 这里的 pattern 会捕获分隔符，所以 split 后列表会是 [文, 标点, 文, 标点...]
    sentences = re.split(r'([。！？!?\n]+)', text)
    
    chunks = []
    current_chunk = ""
    
    for i in range(0, len(sentences), 2):
        sentence_text = sentences[i]
        # 获取对应的标点（如果是最后一段可能没有）
        punctuation = sentences[i+1] if i+1 < len(sentences) else ""
        full_sentence = sentence_text + punctuation
        
        # 如果当前块 + 新句子 超过限制，则先保存当前块，开启新块
        if len(current_chunk) + len(full_sentence) > max_size:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = full_sentence
        else:
            current_chunk += full_sentence
            
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

# ========== 工具函数：JSON 提取与清洗 ==========
def extract_json_from_response(content):
    """尝试从 LLM 回复中提取并解析 JSON"""
    try:
        return json.loads(content)
    except Exception:
        pass
    
    # 尝试提取 markdown 代码块或纯数组
    # 匹配 [ ... ] 结构
    m = re.search(r"(\[.*\])", content, flags=re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return None

# ========== 核心逻辑：处理单个文件 ==========
def process_single_file(txt_path):
    """处理单个TXT文件：切分 -> 逐个转换 -> 合并 -> 保存"""
    print(f"开始处理: {txt_path.name}")
    try:
        full_text = txt_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"读取文件失败 {txt_path}: {e}")
        return None

    # 1. 切分文本
    chunks = split_text_into_chunks(full_text, MAX_CHUNK_SIZE)
    print(f"文件 {txt_path.name} 已切分为 {len(chunks)} 个片段。")

    all_tts_data = [] # 存储最终合并的数据
    
    # 2. 逐个片段处理
    for i, chunk_text in enumerate(chunks):
        if not chunk_text.strip():
            continue
            
        print(f"  > 正在处理片段 {i+1}/{len(chunks)} ({len(chunk_text)}字符)...")
        
        # 构造针对该片段的 Prompt
        # 注意：这里我们告诉 LLM 这只是一个片段
        user_prompt = (
            "你是一个严格的格式化器。\n"
            f"根据下述【规范】将提供的【小说片段】转换为 index-tts v2 有声书 JSON。\n"
            "注意：这只是小说的一小部分，请只处理这段文字，不要编造开头或结尾，直接输出 JSON 数组。\n\n"
            "【规范】如下：\n" + SPEC_PROMPT + "\n"
            "【小说片段】如下：\n" 
            f"'''\n{chunk_text}\n'''\n\n"
            "请直接输出 JSON 数组："
        )
        
        chunk_success = False
        max_chunk_retries = 3 # 每个片段最多重试3次
        
        for attempt in range(max_chunk_retries):
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": user_prompt}],
                    temperature=0.2, # 低温度保证格式稳定
                    max_tokens=1000000, # 给输出留足空间
                )
                
                raw_content = response.choices[0].message.content
                
                # 尝试解析
                parsed_data = extract_json_from_response(raw_content)
                # print(raw_content)
                if isinstance(parsed_data, list):
                    all_tts_data.extend(parsed_data)
                    chunk_success = True
                    break # 成功，跳出重试循环
                else:
                    print(f"    [警告] 片段 {i+1} 第 {attempt+1} 次解析失败：未找到有效列表。重试中...")
            
            except Exception as e:
                print(f"    [错误] 片段 {i+1} 第 {attempt+1} 次 API 调用出错: {e}")
                time.sleep(2) # 简单冷却
        
        if not chunk_success:
            print(f"!!! [严重错误] 文件 {txt_path.name} 的片段 {i+1} 处理彻底失败，跳过该片段 !!!")
            # 记录错误日志，但继续处理下一个片段，以免前功尽弃
            with open("error_logs.txt", "a", encoding="utf-8") as f:
                f.write(f"文件: {txt_path} | 片段: {i+1}\n内容:\n{chunk_text}\n\n")

    # 3. 结果校验与保存
    if not all_tts_data:
        print(f"未能生成任何有效数据: {txt_path}")
        return None

    # 简单校验
    valid_count = 0
    for item in all_tts_data:
        if isinstance(item, dict) and "speaker" in item and "content" in item:
            valid_count += 1
            
    print(f"文件 {txt_path.name} 处理完成，共生成 {valid_count} 条语音数据。")

    json_path = txt_path.with_suffix('.json')
    json_path.write_text(json.dumps(all_tts_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已保存到 {json_path}")
    return json_path

# ========== 任务提示词 (保持不变) ==========
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

# ========== 主函数：并行处理目录下的所有TXT文件 ==========
def main():
    chapters_dir = Path(config.input_dir)
    if not chapters_dir.exists() or not chapters_dir.is_dir():
        raise FileNotFoundError(f"未找到 {config.input_dir} 目录，请确保拆分后的文件在此目录下。")

    txt_files = list(chapters_dir.glob("*.txt"))
    if not txt_files:
        raise FileNotFoundError(f"在 ./{config.input_dir} 目录下未找到任何 .txt 文件。")

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
    max_workers = getattr(config, 'max_workers', 1) 
    with ThreadPoolExecutor(max_workers=min(len(files_to_process), max_workers)) as executor:
        futures = [executor.submit(process_single_file, txt_path) for txt_path in files_to_process]

        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    print(f"完成: {result.name}")
            except Exception as e:
                print(f"处理失败: {e}")

    print("所有文件处理完成！")

if __name__ == "__main__":
    main()