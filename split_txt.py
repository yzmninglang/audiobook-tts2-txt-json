import re
import os

def split_txt_by_chapters(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # 正则表达式匹配二级标题：## 标题
    pattern = r'^## (.+)$'
    matches = list(re.finditer(pattern, content, re.MULTILINE))

    if not matches:
        print("未找到章节切分点。")
        return

    # 获取目录名，从原文件名去掉扩展名
    base_name = os.path.splitext(filename)[0]
    output_dir = f"{base_name}_chapters"
    os.makedirs(output_dir, exist_ok=True)

    for i, match in enumerate(matches):
        start = match.start()
        chapter_title = match.group(1).strip()

        # 找到下一章节的开始或文件末尾
        if i < len(matches) - 1:
            end = matches[i + 1].start()
        else:
            end = len(content)

        # 提取章节内容
        chapter_content = content[start:end]

        # 清理标题中的非法字符（保留中文、英文、数字、下划线）
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
    split_txt_by_chapters("《走到人生边上》杨绛.txt")