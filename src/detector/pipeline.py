"""
Detection pipeline: orchestrates Layer 1-3 and provides the public FileEncodingDetector API.
"""

import logging
from pathlib import Path

from character_token import CharacterToken
from encoding import DETECTION_ORDER, resolve_std_name

from .anchors import _bom_anchor, _is_pure_ascii_bytes, _utf16_structural_anchor
from .decision import _content_discriminator, _run_agents, _softmax


logger = logging.getLogger(__name__)


def detect_with_full_decision(raw_data: bytes) -> dict:
    """Full 3-layer detection pipeline."""
    if not raw_data:
        return {
            "encoding": "UTF-8",
            "std_name": "utf-8",
            "confidence": 1.0,
            "top_candidates": [("UTF-8", 1.0)],
        }

    # ── Layer 1: Anchor Detection ──

    # 1a. BOM
    bom_result = _bom_anchor(raw_data)
    if bom_result:
        name, std = bom_result
        return {
            "encoding": name,
            "std_name": std,
            "confidence": 1.0,
            "top_candidates": [(name, 1.0)],
        }

    # 1b. UTF-16 structural anchor
    utf16_anchor = _utf16_structural_anchor(raw_data)

    # 1c. ASCII short-circuit
    if _is_pure_ascii_bytes(raw_data):
        if utf16_anchor is None:
            return {
                "encoding": "ASCII",
                "std_name": "utf-8",
                "confidence": 1.0,
                "top_candidates": [("ASCII", 1.0)],
            }

    # ── Layer 2: Run All Scoring Agents ──
    scores = _run_agents(raw_data)

    # ── Layer 3: Decision Engine ──

    # 3a. Apply anchor filter
    if utf16_anchor == "LE":
        scores = {k: v for k, v in scores.items() if k in ("UTF-16 LE", "UTF-16 BE")}
        scores["UTF-16 LE"] = max(scores.get("UTF-16 LE", 0), 0.7)
        scores["UTF-16 BE"] = min(scores.get("UTF-16 BE", 0), 0.3)
    elif utf16_anchor == "BE":
        scores = {k: v for k, v in scores.items() if k in ("UTF-16 LE", "UTF-16 BE")}
        scores["UTF-16 BE"] = max(scores.get("UTF-16 BE", 0), 0.7)
        scores["UTF-16 LE"] = min(scores.get("UTF-16 LE", 0), 0.3)

    # 3b. Normalize with softmax
    names = list(scores.keys())
    vals = [scores[n] for n in names]
    probs = _softmax(vals, temperature=10.0)

    ranked = sorted(zip(names, probs), key=lambda x: x[1], reverse=True)

    if not ranked:
        return {
            "encoding": "UTF-8",
            "std_name": "utf-8",
            "confidence": 0.5,
            "top_candidates": [("UTF-8", 0.5)],
        }

    top1_name = ranked[0][0]
    top1_prob = ranked[0][1]
    top2_prob = ranked[1][1] if len(ranked) > 1 else 0.0

    # 3c. Stability rule
    gap = top1_prob - top2_prob
    if gap < 0.05 and len(ranked) > 1:
        det_names = {enc.display_name for enc in DETECTION_ORDER}
        tied = [name for name, prob in ranked if top1_prob - prob < 0.05 and name in det_names]

        if len(tied) >= 2:
            winner = _content_discriminator(tied, raw_data)
            if winner:
                top1_name = winner
            else:
                for enc in DETECTION_ORDER:
                    if enc.display_name in tied:
                        top1_name = enc.display_name
                        break
        elif len(tied) == 1:
            top1_name = tied[0]
        else:
            if scores.get("UTF-8", 0) > 0.5:
                top1_name = "UTF-8"

    std_name = resolve_std_name(top1_name)
    return {
        "encoding": top1_name,
        "std_name": std_name,
        "confidence": round(top1_prob, 4),
        "top_candidates": [(n, round(p, 4)) for n, p in ranked],
    }


# ---------------------------------------------------------------------------
# FileEncodingDetector
# ---------------------------------------------------------------------------

class FileEncodingDetector:
    """Detect file encodings and build per-character tokens."""

    DETECT_ORDER = [(enc.display_name, enc.std_name) for enc in DETECTION_ORDER]

    @classmethod
    def _read_raw(cls, file_path):
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File does not exist: {file_path}")
        with open(file_path, "rb") as f:
            return f.read()

    @classmethod
    def _detect_from_bytes(cls, raw_data):
        result = detect_with_full_decision(raw_data)
        return (result["encoding"], result["std_name"])

    @classmethod
    def detect_file(cls, file_path, raw_data=None):
        if raw_data is None:
            raw_data = cls._read_raw(file_path)
        if not raw_data:
            return ("UTF-8", "utf-8")
        return cls._detect_from_bytes(raw_data)

    @classmethod
    def detect_bytes(cls, raw_data: bytes) -> tuple[str, str]:
        """Detect encoding from raw bytes. Returns (display_name, std_name)."""
        return cls._detect_from_bytes(raw_data)

    @classmethod
    def diagnose_detect(cls, file_path, raw_data=None):
        if raw_data is None:
            raw_data = cls._read_raw(file_path)

        trials = []
        bom = _bom_anchor(raw_data)
        if bom:
            trials.append((f"{bom[0]} BOM", raw_data[:3].hex() if raw_data[:3] != b"" else "", "BOM matched"))

        if len(raw_data) >= 2:
            for label, std in [("UTF-16 (LE, no BOM)", "utf-16-le"),
                               ("UTF-16 (BE, no BOM)", "utf-16-be")]:
                try:
                    raw_data.decode(std)
                    trials.append((label, "", "decoded successfully"))
                except UnicodeDecodeError:
                    trials.append((label, "", "decode failed"))

        for display_name, std_name in cls.DETECT_ORDER:
            try:
                raw_data.decode(std_name)
                trials.append((display_name, "", "decoded successfully"))
            except UnicodeDecodeError as e:
                pos = getattr(e, "start", 0)
                sample = raw_data[max(0, pos):pos + 8].hex()
                trials.append((display_name, sample, "decode failed"))
            except LookupError:
                trials.append((display_name, "", "unsupported encoding"))

        result = detect_with_full_decision(raw_data)
        detected_name = result["encoding"]
        is_pure_ascii = _is_pure_ascii_bytes(raw_data)
        return trials, detected_name, is_pure_ascii

    @staticmethod
    def _make_token(char, display_name, file_path, source_bytes):
        return CharacterToken(
            char=char,
            source_encoding=display_name,
            source_file=str(file_path) if hasattr(file_path, "suffix") else file_path,
            source_bytes=source_bytes,
        )

    @staticmethod
    def charset_detect(raw_data: bytes) -> dict:
        try:
            import charset_normalizer
            result = charset_normalizer.detect(raw_data)
            return {
                "encoding": result.get("encoding", ""),
                "confidence": result.get("confidence", 0),
            }
        except ImportError:
            return {"encoding": "", "confidence": 0}

    @classmethod
    def file_to_tokens(cls, file_path, raw_data=None):
        """读取文件并返回 CharacterToken 列表，保证字节定位不漂移"""
        file_path = Path(file_path)
        if raw_data is None:
            raw_data = cls._read_raw(file_path)
        if not raw_data:
            return []

        display_name, std_name = cls.detect_file(file_path, raw_data=raw_data)

        _bom_len = 0
        _reenc = std_name

        # UTF-16 使用独立路径（不兼容 surrogateescape）
        if std_name in ("utf-16", "utf-16-le", "utf-16-be"):
            return cls._file_to_tokens_utf16(raw_data, display_name, std_name, str(file_path))

        if std_name == "utf-8-sig":
            _reenc = "utf-8"
            _bom_len = 3

        # 使用 surrogateescape 解码，非法字节被映射为 U+DC80-U+DCFF
        text = raw_data.decode(std_name, errors="surrogateescape")

        tokens = []
        byte_pos = _bom_len
        for char in text:
            char_bytes = char.encode(_reenc, errors="surrogateescape")
            source_bytes = raw_data[byte_pos:byte_pos + len(char_bytes)]

            # 代理字符（非法字节）显示为 ?，原始字节保留以备查看
            display_char = "?" if 0xDC00 <= ord(char) <= 0xDCFF else char

            tokens.append(cls._make_token(display_char, display_name, file_path, source_bytes))
            byte_pos += len(char_bytes)

        return tokens

    @classmethod
    def _file_to_tokens_utf16(cls, raw_data, display_name, std_name, file_path):
        """UTF-16 独立路径：不使用 surrogateescape，保留原逻辑"""
        _bom_len = 0
        _reenc = std_name
        if std_name == "utf-16":
            _reenc = "utf-16-le" if raw_data[:2] == b"\xff\xfe" else "utf-16-be"
            _bom_len = 2

        # 使用 std_name（utf-16）解码以自动识别 BOM 并剥离
        text = raw_data.decode(std_name, errors="replace")
        tokens = []
        byte_pos = _bom_len
        for char in text:
            try:
                char_bytes = char.encode(_reenc)
            except UnicodeEncodeError:
                step = 2
                source_bytes = raw_data[byte_pos:byte_pos + step]
                byte_pos += step
                tokens.append(cls._make_token(char, display_name, file_path, source_bytes))
                continue

            source_bytes = raw_data[byte_pos:byte_pos + len(char_bytes)]
            byte_pos += len(char_bytes)
            tokens.append(cls._make_token(char, display_name, file_path, source_bytes))

        return tokens
