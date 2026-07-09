"""
字节级别有效性评分 —— 多字节 CJK 编码的合法序列判定

每种编码（GBK、Big5、Shift-JIS）有不同的合法字节范围。
本模块提供共享的循环框架 + 各编码的独立验证器。
检测原理：逐个字节扫描，统计在合法序列中的字节比例。
"""

from typing import Callable


def score_multibyte_validity(
    raw_data: bytes,
    is_single: Callable[[int], bool],
    is_lead: Callable[[int], bool],
    is_valid_trail: Callable[[int], bool],
) -> float:
    """计算原始字节中构成合法多字节序列的比例

    遍历字节序列，根据回调函数判断每个字节的角色：
      - 单字节字符（如 ASCII）：计为 1 个合法字节，前进 1
      - 前导字节 + 合法后续字节：计为 2 个合法字节，前进 2
      - 非法字节：跳过，不计分

    Args:
        raw_data: 待评估的原始字节序列
        is_single: 判断某字节是否属于合法的单字节字符
        is_lead: 判断某字节是否属于合法的前导字节
        is_valid_trail: 判断某后续字节对于给定的前导字节是否合法

    Returns:
        Float in [0.0, 1.0] — 合法序列中的字节占总字节的比例
    """
    if not raw_data:
        return 0.0
    n = len(raw_data)
    valid = i = 0
    while i < n:
        b = raw_data[i]
        if is_single(b):
            # 单字节合法字符
            valid += 1
            i += 1
        elif is_lead(b) and i + 1 < n:
            # 可能是双字节序列的前导字节，检查后续字节
            tb = raw_data[i + 1]
            if is_valid_trail(tb):
                # 合法的双字节序列，两个字节都计入
                valid += 2
                i += 2
            else:
                # 前导字节后跟非法后续字节，跳过前导字节
                i += 1
        else:
            # 既不是单字节也不是前导字节，跳过
            i += 1
    return valid / n if n else 0.0


# ── GBK 验证器 ────────────────────────────────────────────────────────────────

def _is_single_gbk(b: int) -> bool:
    """GBK 单字节：0x00~0x7F（ASCII 兼容区域）"""
    return b < 0x80


def _is_lead_gbk(b: int) -> bool:
    """GBK 前导字节范围：0x81~0xFE"""
    return 0x81 <= b <= 0xFE


def _is_valid_trail_gbk(tb: int) -> bool:
    """GBK 后续字节范围：0x40~0xFE，排除 0x7F

    注意 GBK 的后续字节范围比 Big5 更大（从 0x40 开始），
    包含 ASCII 可见字符区域，这是 GBK 格式的合法特征。
    """
    return 0x40 <= tb <= 0xFE and tb != 0x7F


def score_gbk(raw_data: bytes) -> float:
    """计算 GBK 合法序列的字节占比"""
    return score_multibyte_validity(
        raw_data,
        is_single=_is_single_gbk,
        is_lead=_is_lead_gbk,
        is_valid_trail=_is_valid_trail_gbk,
    )


# ── Big5 验证器 ───────────────────────────────────────────────────────────────

def _is_lead_big5(b: int) -> bool:
    """Big5 前导字节范围：0xA1~0xF9"""
    return 0xA1 <= b <= 0xF9


def _is_valid_trail_big5(tb: int) -> bool:
    """Big5 后续字节：0x40~0x7E 或 0xA1~0xFE

    Big5 的后续字节有两段，中间有间隔（0x7F~0xA0 为非法），
    这是 Big5 区别于 GBK 的重要特征之一。
    """
    return (0x40 <= tb <= 0x7E) or (0xA1 <= tb <= 0xFE)


def score_big5(raw_data: bytes) -> float:
    """计算 Big5 合法序列的字节占比"""
    return score_multibyte_validity(
        raw_data,
        is_single=lambda b: b < 0x80,   # Big5 单字节同 ASCII
        is_lead=_is_lead_big5,
        is_valid_trail=_is_valid_trail_big5,
    )


# ── Shift-JIS 验证器 ─────────────────────────────────────────────────────────

def _is_single_sjis(b: int) -> bool:
    """Shift-JIS 单字节：0x00~0x7F 或 0xA1~0xDF（半角片假名区）

    Shift-JIS 的特殊之处在于半角片假名（0xA1~0xDF）也属于单字节范畴，
    这是日文编码区别于 GBK/Big5 的独有特征。
    """
    return b < 0x80 or (0xA0 < b < 0xE0)


def _is_lead_sjis(b: int) -> bool:
    """Shift-JIS 前导字节：两段区间 0x81~0x9F 和 0xE0~0xFC

    前导字节的范围被半角片假名区域（0xA1~0xDF）从中断开，
    这种分段设计是 Shift-JIS 的独特模式。
    """
    return (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xFC)


def _is_valid_trail_sjis(tb: int) -> bool:
    """Shift-JIS 后续字节：0x40~0xFC，排除 0x7F

    注意范围从 0x40 开始（包含 @ 等 ASCII 符号），
    到 0xFC 结束，跳过 0x7F（DEL 字符）。
    """
    return 0x40 <= tb <= 0xFC and tb != 0x7F


def score_sjis(raw_data: bytes) -> float:
    """计算 Shift-JIS (cp932) 合法序列的字节占比"""
    return score_multibyte_validity(
        raw_data,
        is_single=_is_single_sjis,
        is_lead=_is_lead_sjis,
        is_valid_trail=_is_valid_trail_sjis,
    )
