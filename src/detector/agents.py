"""
Layer 2: 独立评分 Agent（编码评分层）

每个 Agent 独立评估原始字节属于某种编码的可信度，返回置信度分数（0.0 ~ 1.0）。
各 Agent 互不依赖，结果由 Layer 3 决策引擎合并判定。
"""

from detector.byte_validator import score_gbk, score_big5, score_sjis
from detector.decode_utils import strict_decode
from detector.text_analyzer import analyze_text, char_category, text_script_score


# ── Agent: UTF-8 ──

def _utf8_agent(raw_data: bytes) -> dict[str, float]:
    """UTF-8 Agent：严格解码验证 + ASCII 稀释防护。

    UTF-8 在纯 ASCII 文件中容易被误判（任何 ASCII 文件都是合法 UTF-8），
    因此需要降低低信息量场景的置信度。
    控制字符过多时会进一步扣分，避免二进制数据被误判为文本。
    """
    try:
        text = raw_data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return {"UTF-8": 0.0}

    # ASCII 稀释保护：若无任何非 ASCII 字节，限制最高分为 0.5
    has_non_ascii = any(b >= 128 for b in raw_data)
    if not has_non_ascii:
        return {"UTF-8": 0.5}

    score = 0.95
    ctrl_count = sum(1 for ch in text if char_category(ord(ch)) == "control")
    # 控制字符惩罚：按比例线性扣减，上限 0.15
    ctrl_penalty = min(0.15, ctrl_count * 3 / max(1, len(text)))

    return {"UTF-8": max(0.0, min(1.0, score - ctrl_penalty))}


# ---------------------------------------------------------------------------
# EncodingDetectionAgent — 配置驱动的 CJK 编码检测 Agent
# ---------------------------------------------------------------------------

class EncodingDetectionAgent:
    """配置驱动的 CJK 编码检测 Agent

    替代手写的 _gbk_agent / _big5_agent / _shift_jis_agent。
    每个编码通过 display_name、codec、byte_scorer、feature_weights 唯一确定。
    feature_weights 控制评分公式中各项特征的权重，区分不同编码的关键信号。
    """

    def __init__(self, display_name, codec, byte_scorer, feature_weights):
        """
        Args:
            display_name: 显示名称（如 "GBK"、"Big5"）
            codec: Python 编解码器名称（如 "gbk"、"big5"）
            byte_scorer: 字节级评分函数，返回 0.0 ~ 1.0 的有效字节比例
            feature_weights: 特征权重字典
                - "byte": 字节级评分权重
                - "cjk": CJK 统一表意文字比例权重
                - "script": 文字体系连贯性权重
                - "kana": 假名比例权重（用于 Shift-JIS 区分）
                - "bopomofo": 注音符号比例权重（用于 Big5 区分）
                - "negative_features": dict, 负向特征
                    - "kana": 交叉编码假名惩罚权重（GBK 专用）。
                      尝试用 cp932 解码，若含假名则降低 GBK 分数。
        """
        self.display_name = display_name
        self.codec = codec
        self.byte_scorer = byte_scorer
        self.feature_weights = feature_weights

    def __call__(self, raw_data):
        # 尝试严格解码，失败则返回 0 分
        text = strict_decode(raw_data, self.codec)
        if text is None:
            return {self.display_name: 0.0}

        byte_score = self.byte_scorer(raw_data)
        analysis = analyze_text(text)

        # 空格惩罚：CJK 文本中含有大量空格（>10%）说明可能是误判
        space_penalty = 0.4 if (analysis["cjk_ratio"] > 0 and analysis["space_ratio"] > 0.1) else 0.0
        # 控制字符惩罚：每 1% 控制字符扣 3%，上限 50%
        ctrl_penalty = min(0.5, analysis["control_ratio"] * 3)

        # 加权评分公式：各项特征得分 × 对应特征权重，累加后减去惩罚项
        score = byte_score * self.feature_weights.get("byte", 0)
        if "cjk" in self.feature_weights:
            score += analysis["cjk_ratio"] * self.feature_weights["cjk"]
        if "script" in self.feature_weights:
            score += min(1.0, analysis["script_score"]) * self.feature_weights["script"]
        if "kana" in self.feature_weights:
            score += analysis["kana_ratio"] * self.feature_weights["kana"]
        if "bopomofo" in self.feature_weights:
            score += analysis["bopomofo_ratio"] * self.feature_weights["bopomofo"]

        # 负向特征：存在某些信号时降低得分
        # 用于解决 GBK 误判 Shift-JIS 的问题（日文假名在 GBK 中罕见）
        neg = self.feature_weights.get("negative_features", {})
        for feat_name, feat_weight in neg.items():
            if feat_name == "kana":
                sjis_text = strict_decode(raw_data, "cp932")
                if sjis_text is not None:
                    sjis_analysis = analyze_text(sjis_text)
                    kana_r = sjis_analysis["kana_ratio"]
                    if kana_r > 0.001:
                        penalty = min(0.35, kana_r * feat_weight)
                        score -= penalty

        score -= space_penalty
        score -= ctrl_penalty

        return {self.display_name: max(0.0, min(1.0, score))}


# GBK Agent：字节评分 40% + CJK 比例 30% + 文字连贯性 30%
# negative_features.kana：交叉编码假名惩罚，解决 Shift-JIS 误判为 GBK 的问题。
# 当原始字节同时能被 cp932 解码且含假名时，降低 GBK 分数。
GBK_AGENT = EncodingDetectionAgent(
    display_name="GBK",
    codec="gbk",
    byte_scorer=score_gbk,
    feature_weights={
        "byte": 0.4,
        "cjk": 0.3,
        "script": 0.3,
        "negative_features": {"kana": 0.65},
    },
)

# Big5 Agent：字节评分 40% + CJK 20% + 文字连贯性 20% + 注音符号 20%
# bopomofo 是 Big5 区别于 GBK 的关键特征（Big5 编码包含注音符号区段）
BIG5_AGENT = EncodingDetectionAgent(
    display_name="Big5",
    codec="big5",
    byte_scorer=score_big5,
    feature_weights={"byte": 0.4, "cjk": 0.2, "script": 0.2, "bopomofo": 0.2},
)

# Shift-JIS Agent：字节评分 40% + 假名比例 40% + CJK 20%
# kana 权重最高，因为 Shift-JIS 是唯一原生包含平假名/片假名的编码
SHIFT_JIS_AGENT = EncodingDetectionAgent(
    display_name="Shift-JIS",
    codec="cp932",
    byte_scorer=score_sjis,
    feature_weights={"byte": 0.4, "kana": 0.4, "cjk": 0.2},
)


# ── Agent: UTF-16 LE / BE ──

def _make_utf16_agent(endian):
    """工厂函数：生成 UTF-16 LE 或 BE 检测 agent。

    两个 agent 仅 endian 名称、解码编码名、null 字节偏移不同，
    其余评分逻辑完全一致。

    评分公式融合三项信号：
    1. null 字节比率（结构得分，0.15 ~ 1.0）
    2. 非 ASCII 字符比率（文本真正利用了 UTF-16 的宽编码范围）
    3. 文本质量评分（文字连贯性）
    """
    display_name = f"UTF-16 {endian}"
    codec = f"utf-16-{endian.lower()}"
    null_offset = 1 if endian == "LE" else 0  # LE 看奇数位，BE 看偶数位

    def agent(raw_data):
        # 长度必须为偶数字节（UTF-16 码元为双字节）
        if len(raw_data) < 2 or len(raw_data) % 2 != 0:
            return {display_name: 0.0}
        try:
            text = raw_data.decode(codec)
        except UnicodeDecodeError:
            return {display_name: 0.0}

        # 代理对区域检查：纯代理字符无有效映射，说明不是合法 UTF-16
        if any(0xD800 <= ord(ch) <= 0xDFFF for ch in text):
            return {display_name: 0.0}

        half = len(raw_data) // 2
        nulls = sum(1 for i in range(null_offset, len(raw_data), 2) if raw_data[i] == 0)

        # 物理零门禁（Zero Gate）校验：UTF-16 的 ASCII 字符会有一个 0x00 伴生，
        # 若完全没有 0x00 字节，绝不可能是 UTF-16 编码
        if nulls == 0:
            return {display_name: 0.0}

        null_ratio = nulls / max(1, half)
        # null 得分分段函数：>10% 时线性放大，≤10% 时取固定低分 0.15
        if null_ratio > 0.1:
            null_score = 0.5 + 0.5 * min(1.0, null_ratio * 2)
        else:
            null_score = 0.15

        non_ascii = sum(1 for ch in text if ord(ch) > 0x7F)
        non_ascii_ratio = non_ascii / max(1, len(text))
        text_quality = text_script_score(text)

        # null 稀少时降低文本质量权重，防止纯 ASCII 误入 UTF-16 分支
        quality_weight = 0.2 if null_ratio <= 0.1 else 0.5
        quality_value = text_quality if non_ascii_ratio > 0 else 0.2
        # 最终得分 = null 结构分 × 0.5 + 文本质量 × 质量权重
        score = null_score * 0.5 + quality_value * quality_weight
        return {display_name: max(0.0, min(1.0, score))}

    return agent


_utf16le_agent = _make_utf16_agent("LE")
_utf16be_agent = _make_utf16_agent("BE")


# ── Agent: Extended ASCII ──

def _extended_ascii_agent(raw_data: bytes) -> dict[str, float]:
    """Extended ASCII（cp1252）兜底 Agent。

    作为所有编码都无法匹配时的最后兜底方案，始终返回低置信度。
    纯 ASCII 占 95% 以上时给 0.2，占 50% 以上给 0.1，其余 0.02。
    得分极低，除非所有其他 Agent 都无法解码，否则不会胜出。
    """
    ascii_ratio = sum(1 for b in raw_data if b < 128) / max(1, len(raw_data))
    if ascii_ratio > 0.95:
        return {"Extended ASCII": 0.2}
    if ascii_ratio > 0.5:
        return {"Extended ASCII": 0.1}
    return {"Extended ASCII": 0.02}


# 所有 Agent 有序列表，Layer 3 遍历此列表收集各编码置信度
_ALL_AGENTS = [
    _utf8_agent,              # UTF-8（严格解码 + ASCII 稀释防护）
    GBK_AGENT,                # GBK（配置驱动，字节 + CJK + 文字连贯性）
    BIG5_AGENT,               # Big5（配置驱动，含注音符号特征）
    SHIFT_JIS_AGENT,          # Shift-JIS（配置驱动，假名高权重）
    _utf16le_agent,           # UTF-16 LE（零门禁 + null 结构比）
    _utf16be_agent,           # UTF-16 BE（零门禁 + null 结构比）
    _extended_ascii_agent,    # Extended ASCII（低分兜底）
]
