import re
from fuzzywuzzy import fuzz
import os
import config

# 创建保存章节文件的文件夹
def create_output_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# 读取目录文件
def load_chapter_titles(chap_list_file):
    with open(chap_list_file, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file.readlines()]

# 逐行读取小说并进行章节分割
def split_novel_by_fuzzy_matching(novel_file, chap_list_file):
    # 读取章节标题
    chapter_titles = load_chapter_titles(chap_list_file)

    # 读取小说内容
    with open(novel_file, 'r', encoding='utf-8') as file:
        novel_lines = file.readlines()

    # 收集潜在分割点：title -> list of (line_index, score)
    split_points = {title: [] for title in chapter_titles}

    # 逐行检查每一行与目录中章节的模糊匹配
    for idx, line in enumerate(novel_lines):
        line = line.strip()

        if not line:
            continue  # 跳过空行

        # 对当前行与所有章节标题进行模糊匹配
        best_match_score = 0
        best_match_title = ""

        for title in chapter_titles:
            score = fuzz.ratio(line, title)
            if score > best_match_score:
                best_match_score = score
                best_match_title = title

        # 如果匹配得分高于某个阈值，记录为潜在分割点
        if best_match_score >= 40:  # 阈值可以根据实际情况调整
            split_points[best_match_title].append((idx, best_match_score))

    # 对于每个标题，选择得分最高的分割点
    final_split_points = []
    for title, points in split_points.items():
        if points:
            # 选择得分最高的
            best_point = max(points, key=lambda x: x[1])
            final_split_points.append((best_point[0], title))

    # 按行号排序分割点
    final_split_points.sort(key=lambda x: x[0])

    current_chapter = []
    chapter_num = 1
    current_chapter_title = ""  # 初始化 current_chapter_title

    # 根据小说文件名创建输出文件夹
    novel_name = os.path.splitext(os.path.basename(novel_file))[0]
    output_dir = f"{novel_name}_chapters"
    create_output_dir(output_dir)

    # 逐行处理，遇到分割点时分割
    split_idx = 0
    for idx, line in enumerate(novel_lines):
        line = line.strip()

        if not line:
            continue  # 跳过空行

        # 检查是否是分割点
        if split_idx < len(final_split_points) and idx == final_split_points[split_idx][0]:
            if current_chapter:
                # 保存当前章节内容
                chapter_filename = os.path.join(output_dir, f"P{str(chapter_num).zfill(2)}_{current_chapter_title}.txt")
                with open(chapter_filename, 'w', encoding='utf-8') as chapter_file:
                    chapter_file.write("\n".join(current_chapter))
                print(f"Chapter {chapter_num}: {current_chapter_title} saved as {chapter_filename}")

                # 重置当前章节内容
                current_chapter = []

            # 更新章节编号，并将当前行作为章节内容开始
            current_chapter_title = final_split_points[split_idx][1]
            current_chapter.append(line)
            chapter_num += 1
            split_idx += 1
        else:
            # 如果当前行不是章节标题，将其视为章节内容
            current_chapter.append(line)

    # 处理最后一个章节
    if current_chapter:
        chapter_filename = os.path.join(output_dir, f"P{str(chapter_num).zfill(2)}_{current_chapter_title}.txt")
        with open(chapter_filename, 'w', encoding='utf-8') as chapter_file:
            chapter_file.write("\n".join(current_chapter))
        print(f"Chapter {chapter_num}: {current_chapter_title} saved as {chapter_filename}")

# 调用函数

txtname = config.book_name+".txt"
split_novel_by_fuzzy_matching(
    txtname,       # 小说文本文件
    "chap_list.txt",        # 目录文件
)
