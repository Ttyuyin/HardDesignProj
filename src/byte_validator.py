"""
Byte-level validity scoring for multibyte CJK encodings.

Each encoding (GBK, Big5, Shift-JIS) has different valid byte ranges.
This module provides a shared loop framework + independent validators
for each encoding, extracted from file_detector.py.
"""

from typing import Callable


def score_multibyte_validity(
    raw_data: bytes,
    is_single: Callable[[int], bool],
    is_lead: Callable[[int], bool],
    is_valid_trail: Callable[[int], bool],
) -> float:
    """Proportion of bytes forming valid sequences for a multibyte encoding.

    Args:
        raw_data: The raw byte sequence to evaluate.
        is_single: Function that returns True if byte `b` is a valid single-byte char.
        is_lead: Function that returns True if byte `b` is a valid lead byte.
        is_valid_trail: Function that returns True if trail byte `tb` is valid
                        for the given lead byte.

    Returns:
        Float in [0.0, 1.0] — proportion of bytes in valid sequences.
    """
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


# ── GBK validators ──────────────────────────────────────────────────────────

def _is_single_gbk(b: int) -> bool:
    return b < 0x80


def _is_lead_gbk(b: int) -> bool:
    return 0x81 <= b <= 0xFE


def _is_valid_trail_gbk(tb: int) -> bool:
    return 0x40 <= tb <= 0xFE and tb != 0x7F


def score_gbk(raw_data: bytes) -> float:
    """Proportion of bytes that form valid GBK sequences."""
    return score_multibyte_validity(
        raw_data,
        is_single=_is_single_gbk,
        is_lead=_is_lead_gbk,
        is_valid_trail=_is_valid_trail_gbk,
    )


# ── Big5 validators ─────────────────────────────────────────────────────────

def _is_lead_big5(b: int) -> bool:
    return 0xA1 <= b <= 0xF9


def _is_valid_trail_big5(tb: int) -> bool:
    return (0x40 <= tb <= 0x7E) or (0xA1 <= tb <= 0xFE)


def score_big5(raw_data: bytes) -> float:
    """Proportion of bytes that form valid Big5 sequences."""
    return score_multibyte_validity(
        raw_data,
        is_single=lambda b: b < 0x80,
        is_lead=_is_lead_big5,
        is_valid_trail=_is_valid_trail_big5,
    )


# ── Shift-JIS validators ────────────────────────────────────────────────────

def _is_single_sjis(b: int) -> bool:
    return b < 0x80 or (0xA0 < b < 0xE0)


def _is_lead_sjis(b: int) -> bool:
    return (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xFC)


def _is_valid_trail_sjis(tb: int) -> bool:
    return 0x40 <= tb <= 0xFC and tb != 0x7F


def score_sjis(raw_data: bytes) -> float:
    """Proportion of bytes that form valid Shift-JIS (cp932) sequences."""
    return score_multibyte_validity(
        raw_data,
        is_single=_is_single_sjis,
        is_lead=_is_lead_sjis,
        is_valid_trail=_is_valid_trail_sjis,
    )
