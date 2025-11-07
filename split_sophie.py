import re
import os

def split_sophie_by_chapters(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # 定义章节标题映射（大致匹配）
    chapter_patterns = [
        (r'伊甸园', '1.伊甸园——在某个时刻事物必然从无到有'),
        (r'魔术师的礼帽', '2.魔术师的礼帽——要成为一个优秀的哲学家只有一个条件：要有好奇心'),
        (r'神话', '3.神话——善与恶之间脆弱的平衡'),
        (r'自然派哲学家', '4.自然派哲学家——没有一件事情可以来自空无'),
        (r'德谟克利特斯', '5.德谟克利特斯——世界上最巧妙的玩具'),
        (r'命运', '6.命运——算命者试图预测某些事实上极不可测的事物'),
        (r'苏格拉底', '7.苏格拉底——最聪明的是明白自己无知的人'),
        (r'雅典', '8.雅典——废墟中升起了几栋高楼'),
        (r'柏拉图', '9.柏拉图——回归灵魂世界的渴望'),
        (r'少校的小木屋', '10.少校的小木屋——镜中的女孩双眼眨了一眨'),
        (r'亚里斯多德', '11.亚里斯多德——一位希望澄清我们观念的严谨的逻辑学家'),
        (r'希腊文化', '12.希腊文化——一丝火花'),
        (r'明信片', '13.明信片——我对自己实施严格的检查制度'),
        (r'两种文化', '14.两种文化——避免在真空中飘浮的唯一方式'),
        (r'中世纪', '15.中世纪——对了一部分并不等于错'),
        (r'文艺复兴', '16.文艺复兴——啊！藏在凡俗身躯里的神明子孙呐'),
        (r'巴洛克时期', '17.巴洛克时期——宛如梦中的事物'),
        (r'笛卡尔', '18.笛卡尔——他希望清除工地上所有的瓦砾'),
        (r'史宾诺莎', '19.史宾诺莎——上帝不是一个傀儡戏师傅'),
        (r'洛克', '20.洛克-赤裸、空虚一如教师来到教室前的黑板'),
        (r'休姆', '21.休姆——将它付之一炬'),
        (r'伯克莱', '22.伯克莱——宛如燃烧的恒星旁一颗晕眩的行星'),
        (r'柏客来', '23.柏客来——曾祖母向一名吉普赛妇人买的一面古老魔镜'),
        (r'启蒙', '24.启蒙——从制针的技术到铸造大炮的方法'),
        (r'康德', '25.康德——头上闪烁的星空与心中的道德规范'),
        (r'浪漫主义', '26.浪漫主义——神秘之路通向内心'),
        (r'黑格尔', '27.黑格尔——可以站得住脚的就是有道理的'),
        (r'祁克果', '28.祁克果——欧洲正迈向破产的地步'),
        (r'马克思', '29.马克思——在欧洲游荡的幽灵'),
        (r'达尔文', '30.达尔文——满载基因航行过生命的一艘小船'),
        (r'弗洛伊德', '31.弗洛伊德——他内心出现那股令人讨厌的自大的冲动'),
        (r'我们这个时代', '32.我们这个时代——人注定是要受自由之苦的'),
        (r'花园盛会', '33.花园盛会——一只白色的乌鸦'),
        (r'对位法', '34.对位法——两首或多首旋律齐响'),
        (r'那轰然一响', '35.那轰然一响——我们也是星尘')
    ]

    # 获取目录名，从原文件名去掉扩展名
    base_name = os.path.splitext(filename)[0]
    output_dir = f"{base_name}_chapters"
    os.makedirs(output_dir, exist_ok=True)

    # 找到所有章节开始位置
    chapter_starts = []
    seen_titles = set()

    for pattern, title in chapter_patterns:
        matches = list(re.finditer(pattern, content))
        for match in matches:
            if title not in seen_titles:
                seen_titles.add(title)
                chapter_starts.append((match.start(), title))

    # 按位置排序
    chapter_starts.sort(key=lambda x: x[0])

    for i, (start, title) in enumerate(chapter_starts):
        # 找到下一章节的开始或文件末尾
        if i < len(chapter_starts) - 1:
            end = chapter_starts[i + 1][0]
        else:
            end = len(content)

        # 提取章节内容
        chapter_content = content[start:end]

        # 创建文件名（使用标题作为文件名）
        safe_title = re.sub(r'[^\w\u4e00-\u9fff]', '_', title)  # 替换特殊字符
        filename_out = f"{safe_title}.txt"
        filepath_out = os.path.join(output_dir, filename_out)

        # 写入文件
        with open(filepath_out, 'w', encoding='utf-8') as out_file:
            out_file.write(chapter_content)

        print(f"已创建文件: {filepath_out}")

if __name__ == "__main__":
    split_sophie_by_chapters("苏菲的世界.txt")