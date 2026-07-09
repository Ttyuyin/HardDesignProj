"""
Unicode text analysis utilities — extracted from file_detector.py.

Provides character categorization and statistical analysis of decoded text.
All logic migrated verbatim from the original file_detector.py agents.
"""

from collections import Counter


def char_category(cp: int) -> str:
    """Categorize a Unicode code point for scoring."""
    if 0x20 <= cp <= 0x7E:
        return "ascii"
    if cp < 0x20 or cp == 0x7F:
        return "control"
    if 0x3040 <= cp <= 0x309F:
        return "hiragana"
    if 0x30A0 <= cp <= 0x30FF:
        return "katakana"
    if 0xAC00 <= cp <= 0xD7AF:
        return "hangul"
    if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
        return "cjk"
    if 0x3100 <= cp <= 0x312F:
        return "bopomofo"
    return "other"


def category_weights(category: str) -> float:
    """Weight by script category — higher = more specific to CJK encodings."""
    return {
        "cjk": 5.0, "bopomofo": 3.0, "hangul": 3.0,
        "hiragana": 3.0, "katakana": 3.0,
        "ascii": 1.0, "control": 0.0, "other": 0.5,
    }.get(category, 0.5)


def text_script_score(text: str) -> float:
    """Average script specificity of decoded text."""
    if not text:
        return 0.0
    total = 0.0
    for ch in text:
        total += category_weights(char_category(ord(ch)))
    return total / len(text)


def analyze_text(text: str) -> dict:
    """Analyze decoded text and return comprehensive statistics.

    Returns:
        dict with keys:
            length, cjk_ratio, kana_ratio, bopomofo_ratio,
            hangul_ratio, control_ratio, ascii_ratio,
            space_ratio, script_score, categories
    """
    if not text:
        return {
            "length": 0, "cjk_ratio": 0.0, "kana_ratio": 0.0,
            "bopomofo_ratio": 0.0, "hangul_ratio": 0.0,
            "control_ratio": 0.0, "ascii_ratio": 0.0,
            "space_ratio": 0.0, "script_score": 0.0,
            "categories": Counter(),
        }

    cats = Counter(char_category(ord(ch)) for ch in text)
    total = len(text)
    kana = cats.get("hiragana", 0) + cats.get("katakana", 0)
    space_count = sum(1 for ch in text if ch == " ")

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
