"""
Unicode 文本分析工具 —— 字符分类与统计评分

从 file_detector.py 提取，提供解码后文本的字符分类和统计分析。
每种 CJK 编码的字符分布特征不同，分析结果用于辅助编码检测。
"""

from collections import Counter


def char_category(cp: int) -> str:
    """对 Unicode 码点进行分类，用于后续评分

    根据码点所在的 Unicode 区块判定字符类型：
      ascii      — 标准 ASCII 可见字符（0x20~0x7E）
      control    — 控制字符（0x00~0x1F 及 0x7F）
      hiragana   — 平假名（U+3040~U+309F）
      katakana   — 片假名（U+30A0~U+30FF）
      hangul     — 韩文（U+AC00~U+D7AF）
      cjk        — 中日韩统一表意文字（CJK Unified Ideographs）
      bopomofo   — 注音符号（U+3100~U+312F）
      other      — 其他字符
    """
    if 0x20 <= cp <= 0x7E:               # 标准 ASCII 可见字符（不含 DEL）
        return "ascii"
    if cp < 0x20 or cp == 0x7F:          # C0 控制字符 + DEL
        return "control"
    if 0x3040 <= cp <= 0x309F:           # 平假名区块
        return "hiragana"
    if 0x30A0 <= cp <= 0x30FF:           # 片假名区块
        return "katakana"
    if 0xAC00 <= cp <= 0xD7AF:           # 韩文音节区块
        return "hangul"
    if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:  # CJK 统一表意文字 + 扩展 A
        return "cjk"
    if 0x3100 <= cp <= 0x312F:           # 注音符号
        return "bopomofo"
    return "other"                        # 其他（如标点、数学符号等）


def category_weights(category: str) -> float:
    """按字符分类赋予权重 —— 值越高表示该分类对 CJK 编码的指向性越强

    CJK 相关类别的权重最高（5.0），因为它们的出现强烈暗示文本是 CJK 编码。
    ASCII 权重较低（1.0），因为任何编码都可能包含 ASCII 字符。
    控制字符权重为零，完全不贡献评分。
    """
    return {
        "cjk": 5.0, "bopomofo": 3.0, "hangul": 3.0,
        "hiragana": 3.0, "katakana": 3.0,
        "ascii": 1.0, "control": 0.0, "other": 0.5,
    }.get(category, 0.5)


def text_script_score(text: str) -> float:
    """计算文本的"文字特异性"平均分

    值越高说明文本越"像"某种 CJK 编码。
    例如纯中文文本分数趋近 5.0，纯英文趋近 1.0。
    """
    if not text:
        return 0.0
    total = 0.0
    for ch in text:
        total += category_weights(char_category(ord(ch)))
    return total / len(text)


def analyze_text(text: str) -> dict:
    """分析解码文本，返回全面的字符分类统计

    返回包含各类别占比的 dict，用于编码检测模块综合判断。
    各 ratio 字段说明文本特征，例如 cjk_ratio 高暗示源编码为 GBK/Big5 等。

    Returns:
        dict with keys:
            length, cjk_ratio, kana_ratio, bopomofo_ratio,
            hangul_ratio, control_ratio, ascii_ratio,
            space_ratio, script_score, categories
    """
    if not text:
        # 空文本直接返回全零结果
        return {
            "length": 0, "cjk_ratio": 0.0, "kana_ratio": 0.0,
            "bopomofo_ratio": 0.0, "hangul_ratio": 0.0,
            "control_ratio": 0.0, "ascii_ratio": 0.0,
            "space_ratio": 0.0, "script_score": 0.0,
            "categories": Counter(),
        }

    # 对每个字符分类并计数
    cats = Counter(char_category(ord(ch)) for ch in text)
    total = len(text)
    # 假名 = 平假名 + 片假名
    kana = cats.get("hiragana", 0) + cats.get("katakana", 0)
    # 空格单独统计（空格虽然属于 ASCII，但作为分隔符有特殊意义）
    space_count = sum(1 for ch in text if ch == " ")

    # 文字特异性评分
    script_score_val = text_script_score(text)

    return {
        "length": total,
        "cjk_ratio": cats.get("cjk", 0) / total,
        "kana_ratio": kana / total,
        "bopomofo_ratio": cats.get("bopomofo", 0) / total,
        "hangul_ratio": cats.get("hangul", 0) / total,
        "control_ratio": cats.get("control", 0) / total,
        "ascii_ratio": cats.get("ascii", 0) / total,
        "space_ratio": space_count / total,
        "script_score": script_score_val,
        "categories": cats,
    }
