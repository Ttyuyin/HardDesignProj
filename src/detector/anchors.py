"""Layer 1: Anchor Detector —— 提供确定性事实和弱hint，不做最终判定"""


def run_anchors(raw_data: bytes) -> dict:
    """收集所有锚点证据（BOM、ASCII、UTF-16 结构提示）"""
    bom_result = _bom_anchor(raw_data)
    is_ascii = _is_pure_ascii_bytes(raw_data)
    utf16 = _utf16_structural_anchor(raw_data)

    result = {
        "bom": bom_result,
        "is_ascii": is_ascii,
        "ascii_char_count": len(raw_data),
        "utf16_hint": {
            "endian": utf16["endian"],
            "ratio": utf16["ratio"],
            "hint_strength": utf16["hint_strength"],
        },
    }
    return result


def _bom_anchor(raw_data: bytes) -> dict | None:
    """检测 BOM 签名（UTF-8/UTF-16 LE/BE）"""
    if raw_data[:3] == b"\xef\xbb\xbf":
        return {"encoding": "UTF-8", "std_name": "utf-8-sig", "confidence": 1.0}
    if raw_data[:2] == b"\xff\xfe":
        return {"encoding": "UTF-16 LE", "std_name": "utf-16", "confidence": 1.0}
    if raw_data[:2] == b"\xfe\xff":
        return {"encoding": "UTF-16 BE", "std_name": "utf-16", "confidence": 1.0}
    return None


def _is_pure_ascii_bytes(raw_data: bytes) -> bool:
    """判断所有字节是否均为 ASCII（< 0x80）"""
    return all(b < 128 for b in raw_data)


def _utf16_structural_anchor(raw_data: bytes) -> dict:
    """通过 null 字节分布比率推断 UTF-16 字节序"""
    if len(raw_data) < 2:
        return {"endian": None, "ratio": 0.0, "hint_strength": 0.0}

    usable_len = len(raw_data) - 1 if len(raw_data) % 2 != 0 else len(raw_data)
    half = usable_len // 2
    even_nulls = sum(1 for i in range(0, usable_len, 2) if raw_data[i] == 0)
    odd_nulls = sum(1 for i in range(1, usable_len, 2) if raw_data[i] == 0)
    even_ratio = even_nulls / half
    odd_ratio = odd_nulls / half

    if even_ratio > 0.25:
        hint_strength = min(1.0, even_ratio * 1.5)
        return {"endian": "BE", "ratio": even_ratio, "hint_strength": hint_strength}
    if odd_ratio > 0.25:
        hint_strength = min(1.0, odd_ratio * 1.5)
        return {"endian": "LE", "ratio": odd_ratio, "hint_strength": hint_strength}
    return {"endian": None, "ratio": 0.0, "hint_strength": 0.0}
