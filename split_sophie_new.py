import re
import os

def split_sophie_by_dynamic_chapters(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # 找到所有以^开头的章节标题行
    chapter_pattern = r'^(\^.*)$'
    matches = list(re.finditer(chapter_pattern, content, re.MULTILINE))

    # 获取目录名，从原文件名去掉扩展名
    base_name = os.path.splitext(filename)[0]
    output_dir = f"{base_name}_chapters"
    os.makedirs(output_dir, exist_ok=True)

    for i, match in enumerate(matches):
        # 提取标题，去掉^
        title_line = match.group(1).strip()
        title = title_line[1:].strip()  # 去掉^

        # 序号，两位数
        chapter_num = f"{i+1:02d}"

        # 文件名
        safe_title = re.sub(r'[^\w\u4e00-\u9fff]', '_', title)
        filename_out = f"P{chapter_num}_{safe_title}.txt"
        filepath_out = os.path.join(output_dir, filename_out)

        # 找到章节内容：从当前标题到下一个标题或文件末尾
        start = match.start()
        if i < len(matches) - 1:
            end = matches[i + 1].start()
        else:
            end = len(content)

        chapter_content = content[start:end]

        # 写入文件
        with open(filepath_out, 'w', encoding='utf-8') as out_file:
            out_file.write(chapter_content)

        print(f"已创建文件: {filepath_out}")

if __name__ == "__main__":
    split_sophie_by_dynamic_chapters("苏菲的世界.txt")