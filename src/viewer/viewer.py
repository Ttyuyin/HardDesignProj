"""编码查看模块 —— 逐字符展示各编码的字节表示"""

import unicodedata

from shared.display_utils import bytes_to_hex, codepoint_display
from encoding import ENCODING_NAMES, VIEWER_ENCODING_MAP


class EncodingViewer:

    SUPPORTED_ENCODINGS = VIEWER_ENCODING_MAP

    COLUMN_ORDER = ["Char", "Unicode", "Raw Bytes"] + ENCODING_NAMES[:]

    CONTROL_CHAR_MAP = {
        0x00: "NUL", 0x01: "SOH", 0x02: "STX", 0x03: "ETX",
        0x04: "EOT", 0x05: "ENQ", 0x06: "ACK", 0x07: "BEL",
        0x08: "BS",  0x09: "TAB", 0x0A: "LF",  0x0B: "VT",
        0x0C: "FF",  0x0D: "CR",  0x0E: "SO",  0x0F: "SI",
        0x10: "DLE", 0x11: "DC1", 0x12: "DC2", 0x13: "DC3",
        0x14: "DC4", 0x15: "NAK", 0x16: "SYN", 0x17: "ETB",
        0x18: "CAN", 0x19: "EM",  0x1A: "SUB", 0x1B: "ESC",
        0x1C: "FS",  0x1D: "GS",  0x1E: "RS",  0x1F: "US",
        0x7F: "DEL",
    }

    @classmethod
    def get_display_char(cls, char):
        """将控制/空白字符替换为可读标记"""
        code = ord(char)
        if code in cls.CONTROL_CHAR_MAP:
            return f"[{cls.CONTROL_CHAR_MAP[code]}]"
        if code == 0x20:
            return "[SP]"
        if code == 0xA0:
            return "[NBSP]"
        if unicodedata.category(char) == "Cc":
            return f"[U+{code:04X}]"
        return char

    @classmethod
    def analyze_character(cls, char, source_encoding="", source_bytes=b"",
                          fallback_encoding=""):
        """分析单个字符在各编码中的十六进制表示"""
        result = {
            "Char": cls.get_display_char(char),
            "Unicode": codepoint_display(char),
            "Source Encoding": source_encoding,
        }

        for display_name, std_name in cls.SUPPORTED_ENCODINGS.items():
            try:
                encoded_bytes = char.encode(std_name)
                result[display_name] = bytes_to_hex(encoded_bytes)
            except (UnicodeEncodeError, UnicodeDecodeError):
                result[display_name] = "N/A"

        if source_bytes:
            result["Raw Bytes"] = bytes_to_hex(source_bytes)
        elif source_encoding and result.get(source_encoding, "N/A") != "N/A":
            result["Raw Bytes"] = result[source_encoding]
        elif fallback_encoding and result.get(fallback_encoding, "N/A") != "N/A":
            result["Raw Bytes"] = result[fallback_encoding]
        else:
            result["Raw Bytes"] = ""

        return result

    @classmethod
    def analyze_token(cls, token, fallback_encoding=""):
        """分析单个 CharacterToken 在各编码下的表示"""
        return cls.analyze_character(
            token.char,
            source_encoding=token.source_encoding,
            source_bytes=token.source_bytes,
            fallback_encoding=fallback_encoding,
        )

    @classmethod
    def analyze_tokens(cls, tokens, fallback_encoding=""):
        """批量分析 token 列表"""
        return [cls.analyze_token(t, fallback_encoding=fallback_encoding) for t in tokens]

    @classmethod
    def get_statistics(cls, results):
        """统计每个编码的可编码字符数及覆盖率"""
        total = len(results)
        stats = {}
        for enc_name in cls.SUPPORTED_ENCODINGS:
            supported = sum(1 for r in results if r.get(enc_name) != "N/A")
            unsupported = total - supported
            rate = (supported / total * 100) if total > 0 else 0
            stats[enc_name] = {
                "supported": supported,
                "unsupported": unsupported,
                "rate": rate,
                "total": total,
            }
        return {"total_chars": total, "encoding_stats": stats}
