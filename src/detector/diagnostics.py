"""Diagnostic helpers for encoding detection."""

from encoding import DETECTION_ORDER

from .anchors import run_anchors
from .pipeline import detect_with_full_decision


def diagnose_bytes(raw_data: bytes) -> tuple[list[tuple[str, str, str]], str, bool]:
    """诊断字节序列：返回各编码解码尝试、检测结果、纯 ASCII 标志"""
    anchors = run_anchors(raw_data)

    trials = []
    bom = anchors["bom"]
    if bom:
        sample = raw_data[:3].hex() if raw_data[:3] != b"" else ""
        trials.append((f"{bom['encoding']} BOM", sample, "BOM matched"))

    utf16 = anchors["utf16_hint"]
    if utf16["endian"]:
        label = f"UTF-16 ({utf16['endian']}, no BOM)"
        hint = f"null-byte ratio={utf16['ratio']:.2f}"
        trials.append((label, "", hint))

    for encoding in DETECTION_ORDER:
        try:
            raw_data.decode(encoding.std_name)
            trials.append((encoding.display_name, "", "decoded successfully"))
        except UnicodeDecodeError as exc:
            pos = getattr(exc, "start", 0)
            sample = raw_data[max(0, pos):pos + 8].hex()
            trials.append((encoding.display_name, sample, "decode failed"))
        except LookupError:
            trials.append((encoding.display_name, "", "unsupported encoding"))

    result = detect_with_full_decision(raw_data)
    return trials, result["encoding"], anchors["is_ascii"]
