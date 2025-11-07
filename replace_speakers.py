import json
import os
from pathlib import Path

def load_speaker_classifications(classification_file):
    """
    加载 speaker 分类文件
    """
    with open(classification_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def create_speaker_mapping(classifications):
    """
    创建 speaker 到分类的映射字典
    """
    mapping = {}
    for category, speakers in classifications.items():
        for speaker in speakers:
            mapping[speaker] = category
    return mapping

def replace_speakers_in_json(json_file_path, speaker_mapping):
    """
    在单个 JSON 文件中替换 speaker
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    modified = False
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and 'speaker' in item:
                original_speaker = item['speaker']
                if original_speaker in speaker_mapping:
                    item['speaker'] = speaker_mapping[original_speaker]
                    modified = True

    if modified:
        # 备份原文件
        backup_path = json_file_path.with_suffix('.json.backup')
        if not backup_path.exists():
            json_file_path.rename(backup_path)

        # 保存修改后的文件
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"已修改: {json_file_path}")
        return True

    return False

def main():
    # 分类文件路径
    import config
    classification_file = f"{config.json_book_name}_speaker_classifications.json"

    if not os.path.exists(classification_file):
        print(f"分类文件不存在: {classification_file}")
        return

    # 加载分类数据
    classification_data = load_speaker_classifications(classification_file)
    classifications = classification_data.get('classifications', {})
    folder_path = classification_data.get('folder', config.json_book_name)

    # 创建映射
    speaker_mapping = create_speaker_mapping(classifications)
    print(f"加载了 {len(speaker_mapping)} 个 speaker 映射关系")

    # 处理文件夹中的所有 JSON 文件
    json_files = list(Path(folder_path).glob("*.json"))
    if not json_files:
        print(f"在 {folder_path} 中未找到 JSON 文件")
        return

    modified_count = 0
    for json_file in json_files:
        if replace_speakers_in_json(json_file, speaker_mapping):
            modified_count += 1

    print(f"\n处理完成！")
    print(f"总文件数: {len(json_files)}")
    print(f"修改文件数: {modified_count}")
    print(f"跳过文件数: {len(json_files) - modified_count}")

if __name__ == "__main__":
    main()