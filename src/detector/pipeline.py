"""Byte-level encoding detection pipeline. 仅协调 Layer 1-3。"""

from .anchors import run_anchors
from .agents import run_agents
from .decision import decide


_ASCII_SHORT_CIRCUIT_MIN_LEN = 10


def _build_deterministic_result(encoding: str, std_name: str) -> dict:
    """构造确定性检测结果（BOM/ASCII 短路）"""
    return {
        "encoding": encoding,
        "std_name": std_name,
        "confidence": 1.0,
        "top_candidates": [(encoding, 1.0)],
    }


def detect_with_full_decision(raw_data: bytes) -> dict:
    """完整检测流程：L1 锚点 -> L2 Agent 评分 -> L3 决策"""
    if not raw_data:
        return _build_deterministic_result("UTF-8", "utf-8")

    anchors = run_anchors(raw_data)

    if anchors["bom"]:
        return _build_deterministic_result(
            anchors["bom"]["encoding"],
            anchors["bom"]["std_name"],
        )

    if anchors["is_ascii"] and not anchors["utf16_hint"]["endian"]:
        if anchors["ascii_char_count"] >= _ASCII_SHORT_CIRCUIT_MIN_LEN:
            return _build_deterministic_result("ASCII", "utf-8")

    scores = run_agents(raw_data, anchors)
    return decide(scores, raw_data)

