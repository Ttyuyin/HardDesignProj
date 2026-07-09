"""
Layer 2: Independent Scoring Agents

Each agent evaluates raw bytes for a specific encoding and returns a confidence score.
"""

from byte_validator import score_gbk, score_big5, score_sjis
from decode_utils import strict_decode
from text_analyzer import analyze_text, char_category, text_script_score


# ── Agent: UTF-8 ──

def _utf8_agent(raw_data: bytes) -> dict[str, float]:
    """UTF-8: strict decode validation + protection against dilution in ASCII-heavy files."""
    try:
        raw_data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return {"UTF-8": 0.0}

    has_non_ascii = any(b >= 128 for b in raw_data)
    if not has_non_ascii:
        return {"UTF-8": 0.5}

    score = 0.95
    text = raw_data.decode("utf-8")
    ctrl_count = sum(1 for ch in text if char_category(ord(ch)) == "control")
    ctrl_penalty = min(0.15, ctrl_count * 3 / max(1, len(text)))

    return {"UTF-8": max(0.0, min(1.0, score - ctrl_penalty))}


# ---------------------------------------------------------------------------
# EncodingDetectionAgent — 配置驱动的 CJK 编码检测 Agent
# ---------------------------------------------------------------------------

class EncodingDetectionAgent:
    """配置驱动的编码检测 Agent

    替代手写的 _gbk_agent / _big5_agent / _shift_jis_agent。
    每个编码通过 display_name、codec、byte_scorer、feature_weights 唯一确定。
    评分逻辑与原始函数完全一致。
    """

    def __init__(self, display_name, codec, byte_scorer, feature_weights):
        self.display_name = display_name
        self.codec = codec
        self.byte_scorer = byte_scorer
        self.feature_weights = feature_weights

    def __call__(self, raw_data):
        text = strict_decode(raw_data, self.codec)
        if text is None:
            return {self.display_name: 0.0}

        byte_score = self.byte_scorer(raw_data)
        analysis = analyze_text(text)

        space_penalty = 0.4 if (analysis["cjk_ratio"] > 0 and analysis["space_ratio"] > 0.1) else 0.0
        ctrl_penalty = min(0.5, analysis["control_ratio"] * 3)

        score = byte_score * self.feature_weights.get("byte", 0)
        if "cjk" in self.feature_weights:
            score += analysis["cjk_ratio"] * self.feature_weights["cjk"]
        if "script" in self.feature_weights:
            score += min(1.0, analysis["script_score"]) * self.feature_weights["script"]
        if "kana" in self.feature_weights:
            score += analysis["kana_ratio"] * self.feature_weights["kana"]
        if "bopomofo" in self.feature_weights:
            score += analysis["bopomofo_ratio"] * self.feature_weights["bopomofo"]

        score -= space_penalty
        score -= ctrl_penalty

        return {self.display_name: max(0.0, min(1.0, score))}


GBK_AGENT = EncodingDetectionAgent(
    display_name="GBK",
    codec="gbk",
    byte_scorer=score_gbk,
    feature_weights={"byte": 0.4, "cjk": 0.3, "script": 0.3},
)

BIG5_AGENT = EncodingDetectionAgent(
    display_name="Big5",
    codec="big5",
    byte_scorer=score_big5,
    feature_weights={"byte": 0.4, "cjk": 0.2, "script": 0.2, "bopomofo": 0.2},
)

SHIFT_JIS_AGENT = EncodingDetectionAgent(
    display_name="Shift-JIS",
    codec="cp932",
    byte_scorer=score_sjis,
    feature_weights={"byte": 0.4, "kana": 0.4, "cjk": 0.2},
)


# ── Agent: UTF-16 LE / BE ──

def _make_utf16_agent(endian):
    """工厂：生成 UTF-16 LE 或 BE 检测 agent。

    两个 agent 仅 endian 名称、解码编码名、null 字节偏移不同，
    其余评分逻辑完全一致（物理零门禁、结构 null 比率、文本质量）。
    """
    display_name = f"UTF-16 {endian}"
    codec = f"utf-16-{endian.lower()}"
    null_offset = 1 if endian == "LE" else 0

    def agent(raw_data):
        if len(raw_data) < 2 or len(raw_data) % 2 != 0:
            return {display_name: 0.0}
        try:
            text = raw_data.decode(codec)
        except UnicodeDecodeError:
            return {display_name: 0.0}

        if any(0xD800 <= ord(ch) <= 0xDFFF for ch in text):
            return {display_name: 0.0}

        half = len(raw_data) // 2
        nulls = sum(1 for i in range(null_offset, len(raw_data), 2) if raw_data[i] == 0)

        # 物理零门禁校验：若无任何 0x00 字节，绝不可能是 UTF-16
        if nulls == 0:
            return {display_name: 0.0}

        null_ratio = nulls / max(1, half)
        if null_ratio > 0.1:
            null_score = 0.5 + 0.5 * min(1.0, null_ratio * 2)
        else:
            null_score = 0.15

        non_ascii = sum(1 for ch in text if ord(ch) > 0x7F)
        non_ascii_ratio = non_ascii / max(1, len(text))
        text_quality = text_script_score(text)

        quality_weight = 0.2 if null_ratio <= 0.1 else 0.5
        quality_value = text_quality if non_ascii_ratio > 0 else 0.2
        score = null_score * 0.5 + quality_value * quality_weight
        return {display_name: max(0.0, min(1.0, score))}

    return agent


_utf16le_agent = _make_utf16_agent("LE")
_utf16be_agent = _make_utf16_agent("BE")


# ── Agent: Extended ASCII ──

def _extended_ascii_agent(raw_data: bytes) -> dict[str, float]:
    """Extended ASCII (cp1252): catch-all with low baseline."""
    ascii_ratio = sum(1 for b in raw_data if b < 128) / max(1, len(raw_data))
    if ascii_ratio > 0.95:
        return {"Extended ASCII": 0.2}
    if ascii_ratio > 0.5:
        return {"Extended ASCII": 0.1}
    return {"Extended ASCII": 0.02}


_ALL_AGENTS = [
    _utf8_agent,
    GBK_AGENT,
    BIG5_AGENT,
    SHIFT_JIS_AGENT,
    _utf16le_agent,
    _utf16be_agent,
    _extended_ascii_agent,
]
