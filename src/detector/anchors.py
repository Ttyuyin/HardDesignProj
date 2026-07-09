"""
Layer 1: Anchor Detector (Hard Rules)

BOM detection, pure-ASCII check, UTF-16 structural heuristics.
"""


def _bom_anchor(raw_data: bytes) -> tuple[str, str] | None:
    """Check BOM signatures. Returns (display_name, std_name) or None."""
    if raw_data[:3] == b"\xef\xbb\xbf":
        return ("UTF-8", "utf-8-sig")
    if raw_data[:2] == b"\xff\xfe":
        return ("UTF-16 LE", "utf-16")
    if raw_data[:2] == b"\xfe\xff":
        return ("UTF-16 BE", "utf-16")
    return None


def _is_pure_ascii_bytes(raw_data: bytes) -> bool:
    """All bytes < 128."""
    return all(b < 128 for b in raw_data)


def _utf16_structural_anchor(raw_data: bytes) -> str | None:
    """Strong UTF-16 structural evidence via null-byte ratio."""
    length = len(raw_data)
    if length < 2:
        return None
    usable_len = length - 1 if length % 2 != 0 else length
    half = usable_len // 2
    even_nulls = sum(1 for i in range(0, usable_len, 2) if raw_data[i] == 0)
    odd_nulls = sum(1 for i in range(1, usable_len, 2) if raw_data[i] == 0)
    even_ratio = even_nulls / half
    odd_ratio = odd_nulls / half
    if even_ratio > 0.25:
        return "BE"
    if odd_ratio > 0.25:
        return "LE"
    return None
