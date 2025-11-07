import re
import os

def split_laozi_by_chapters(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # 定义章节标题列表（根据用户提供的目录）
    chapter_titles = [
        "社会运转的底层逻辑",
        "贫穷的本质",
        "贫穷的陷阱",
        "阶级卵巢彩票",
        "富人的生财之道",
        "掌握语言的魅力",
        "31",
        "幽默的法则",
        "牧场人脉法",
        "如何通过蛛丝马迹阅读一个人",
        "心理利用成为人际关系的大赢家",
        "高段位有钱人的全脑思维",
        "高手的向上生长和向下兼容",
        "建立信任技巧",
        "一秒看透事物本质",
        "与领导保持良好关系",
        "与同事相处5大技巧",
        "如何在职场快速完成升职加薪",
        "职场饭局的所有学问",
        "领导力",
        "成为领导需掌握的8大手段"
    ]

    # 获取目录名，从原文件名去掉扩展名
    base_name = os.path.splitext(filename)[0]
    output_dir = f"{base_name}_chapters"
    os.makedirs(output_dir, exist_ok=True)

    seen_titles = set()
    chapter_starts = []

    for title in chapter_titles:
        # 使用正则表达式查找标题（允许标题前后有空白字符）
        pattern = r'(?<!\w)' + re.escape(title) + r'(?!\w)'
        match = re.search(pattern, content)
        if match and title not in seen_titles:
            seen_titles.add(title)
            chapter_starts.append((match.start(), title))

    for i, (start, title) in enumerate(chapter_starts):
        # 找到下一章节的开始或文件末尾
        if i < len(chapter_starts) - 1:
            end = chapter_starts[i + 1][0]
        else:
            end = len(content)

        # 提取章节内容
        chapter_content = content[start:end]

        # 创建文件名（格式：P@原标题，其中@为三位数编号）
        chapter_num = f"{i+1:03d}"  # 从001开始编号
        safe_title = re.sub(r'[^\w\u4e00-\u9fff]', '_', title)
        filename_out = f"P{chapter_num}_{safe_title}.txt"
        filepath_out = os.path.join(output_dir, filename_out)

        # 写入文件
        with open(filepath_out, 'w', encoding='utf-8') as out_file:
            out_file.write(chapter_content)

        print(f"已创建文件: {filepath_out}")

if __name__ == "__main__":
    split_laozi_by_chapters("老子的逆袭人生.txt")