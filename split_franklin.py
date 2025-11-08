import re
import os
import difflib

def extract_chapter_titles(filename):
    """从列表文件中提取章节标题"""
    chapters = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('第') and not line.startswith('附录'):
                chapters.append(line)
    return chapters

def fuzzy_match(text, pattern, threshold=0.8):
    """模糊匹配函数，使用相似度"""
    # 移除标点和空格进行匹配
    text_clean = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
    pattern_clean = re.sub(r'[^\w\u4e00-\u9fff]', '', pattern)
    similarity = difflib.SequenceMatcher(None, text_clean, pattern_clean).ratio()
    return similarity >= threshold

def split_franklin_by_chapters(source_file, chapter_list_file):
    chapters = extract_chapter_titles(chapter_list_file)

    # 创建输出目录
    base_name = os.path.splitext(source_file)[0]
    output_dir = f"{base_name}_chapters"
    os.makedirs(output_dir, exist_ok=True)

    chapter_positions = []
    current_chapter = None

    # 逐行读取源文件，寻找章节开始
    with open(source_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line:
                for chapter in chapters:
                    if fuzzy_match(line, chapter):
                        if current_chapter is not None:
                            chapter_positions.append((current_chapter, start_line, line_num - 1))
                        current_chapter = chapter
                        start_line = line_num
                        break

    # 处理最后一个章节
    if current_chapter is not None:
        with open(source_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            chapter_positions.append((current_chapter, start_line, len(lines)))

    # 写入章节文件
    with open(source_file, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()

    for i, (chapter_title, start, end) in enumerate(chapter_positions):
        chapter_content = ''.join(all_lines[start-1:end])

        # 清理标题中的非法字符
        safe_title = re.sub(r'[^\w\u4e00-\u9fff]', '_', chapter_title)

        # 创建文件名：Pxx_标题.txt
        chapter_num = f"{i+1:02d}"
        filename_out = f"P{chapter_num}_{safe_title}.txt"
        filepath_out = os.path.join(output_dir, filename_out)

        # 写入文件
        with open(filepath_out, 'w', encoding='utf-8') as out_file:
            out_file.write(chapter_content)

        print(f"已创建文件: {filepath_out}")

if __name__ == "__main__":
    split_franklin_by_chapters("富兰克林自传.txt", "franklin_list.txt")