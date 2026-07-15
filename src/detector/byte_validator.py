"""字节级别有效性评分 —— GBK/Big5/Shift-JIS 合法序列判定"""

from typing import Callable


def score_multibyte_validity(
    raw_data: bytes,
    is_single: Callable[[int], bool],
    is_lead: Callable[[int], bool],
    is_valid_trail: Callable[[int], bool],
) -> float:
    """计算原始字节中构成合法多字节序列的比例 [0, 1]"""
    if not raw_data:
        return 0.0
    n = len(raw_data)
    valid = i = 0
    while i < n:
        b = raw_data[i]
        if is_single(b):
            valid += 1
            i += 1
        elif is_lead(b) and i + 1 < n:
            tb = raw_data[i + 1]
            if is_valid_trail(tb):
                valid += 2
                i += 2
            else:
                i += 1
        else:
            i += 1
    return valid / n if n else 0.0


def _is_single_gbk(b: int) -> bool:
    """GBK 单字节：< 0x80"""
    return b < 0x80


def _is_lead_gbk(b: int) -> bool:
    """GBK 前导字节范围"""
    return 0x81 <= b <= 0xFE


def _is_valid_trail_gbk(tb: int) -> bool:
    """GBK 尾随字节范围（排除 0x7F）"""
    return 0x40 <= tb <= 0xFE and tb != 0x7F


def score_gbk(raw_data: bytes) -> float:
    """计算 GBK 字节格式合法比例"""
    return score_multibyte_validity(
        raw_data,
        is_single=_is_single_gbk,
        is_lead=_is_lead_gbk,
        is_valid_trail=_is_valid_trail_gbk,
    )


def _is_lead_big5(b: int) -> bool:
    """Big5 前导字节范围"""
    return 0xA1 <= b <= 0xF9


def _is_valid_trail_big5(tb: int) -> bool:
    """Big5 尾随字节范围（0x40~0x7E 或 0xA1~0xFE）"""
    return (0x40 <= tb <= 0x7E) or (0xA1 <= tb <= 0xFE)


def score_big5(raw_data: bytes) -> float:
    """计算 Big5 字节格式合法比例"""
    return score_multibyte_validity(
        raw_data,
        is_single=lambda b: b < 0x80,
        is_lead=_is_lead_big5,
        is_valid_trail=_is_valid_trail_big5,
    )


def _is_single_sjis(b: int) -> bool:
    """Shift-JIS 单字节：ASCII 或半角片假名"""
    return b < 0x80 or (0xA0 < b < 0xE0)


def _is_lead_sjis(b: int) -> bool:
    """Shift-JIS 前导字节范围"""
    return (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xFC)


def _is_valid_trail_sjis(tb: int) -> bool:
    """Shift-JIS 尾随字节范围（排除 0x7F）"""
    return 0x40 <= tb <= 0xFC and tb != 0x7F


def score_sjis(raw_data: bytes) -> float:
    """计算 Shift-JIS 字节格式合法比例"""
    return score_multibyte_validity(
        raw_data,
        is_single=_is_single_sjis,
        is_lead=_is_lead_sjis,
        is_valid_trail=_is_valid_trail_sjis,
    )
