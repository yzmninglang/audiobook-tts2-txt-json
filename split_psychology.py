import re
import os

def split_psychology_by_lectures(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用正则表达式匹配章节标题：第xxx讲
    pattern = r'第([一二三四五六七八九十\d]+)讲'
    matches = list(re.finditer(pattern, content))

    if not matches:
        print("未找到章节切分点。")
        return

    # 获取目录名，从原文件名去掉扩展名
    base_name = os.path.splitext(filename)[0]
    output_dir = f"{base_name}_chapters"
    os.makedirs(output_dir, exist_ok=True)

    seen_chapters = set()
    chapter_starts = []

    for match in matches:
        chapter_num = match.group(1)
        if chapter_num not in seen_chapters:
            seen_chapters.add(chapter_num)
            chapter_starts.append(match)

    for i, match in enumerate(chapter_starts):
        start = match.start()
        chapter_title = match.group(0).strip()  # 如 "第一讲"

        # 找到下一章节的开始或文件末尾
        if i < len(chapter_starts) - 1:
            end = chapter_starts[i + 1].start()
        else:
            end = len(content)

        # 提取章节内容
        chapter_content = content[start:end]

        # 创建文件名
        filename_out = f"{chapter_title}.txt"
        filepath_out = os.path.join(output_dir, filename_out)

        # 写入文件
        with open(filepath_out, 'w', encoding='utf-8') as out_file:
            out_file.write(chapter_content)

        print(f"已创建文件: {filepath_out}")

if __name__ == "__main__":
    split_psychology_by_lectures("分析心理学的理论与实践.txt")