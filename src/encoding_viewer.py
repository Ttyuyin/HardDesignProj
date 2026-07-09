"""
编码查看模块
提供字符级别的编码分析，逐字符展示各编码的字节表示
用于 UI 中的编码查看器表格，让用户直观对比同一字符在不同编码下的字节形态。
"""

import unicodedata

from display_utils import bytes_to_hex, codepoint_display
from encoding import ENCODING_NAMES, VIEWER_ENCODING_MAP


class EncodingViewer:
    """编码查看器，对文本逐字符分析各编码的十六进制表示

    核心功能：给定一个字符，计算它在所有支持编码下的字节序列。
    结果以表格形式展示，用户可直观对比 ASCII/GBK/UTF-8 等的编码差异。
    """

    # 查看器用的编码映射（UTF-16 LE/BE 直接使用对应编解码器）
    SUPPORTED_ENCODINGS = VIEWER_ENCODING_MAP

    # 分析结果列的顺序：字符本身 → Unicode 码点 → 原始字节 → 各编码列
    COLUMN_ORDER = ["Char", "Unicode", "Raw Bytes"] + ENCODING_NAMES[:]

    # ASCII / ISO-646 控制字符名称映射表（C0 集 + DEL）
    # 用于在 UI 中将不可见控制字符替换为可读的缩写标记
    CONTROL_CHAR_MAP = {
        # C0 控制字符 (0x00~0x1F)
        0x00: "NUL", 0x01: "SOH", 0x02: "STX", 0x03: "ETX",
        0x04: "EOT", 0x05: "ENQ", 0x06: "ACK", 0x07: "BEL",
        0x08: "BS",  0x09: "TAB", 0x0A: "LF",  0x0B: "VT",
        0x0C: "FF",  0x0D: "CR",  0x0E: "SO",  0x0F: "SI",
        0x10: "DLE", 0x11: "DC1", 0x12: "DC2", 0x13: "DC3",
        0x14: "DC4", 0x15: "NAK", 0x16: "SYN", 0x17: "ETB",
        0x18: "CAN", 0x19: "EM",  0x1A: "SUB", 0x1B: "ESC",
        0x1C: "FS",  0x1D: "GS",  0x1E: "RS",  0x1F: "US",
        # DEL 字符 (0x7F)
        0x7F: "DEL",
    }

    @classmethod
    def get_display_char(cls, char):
        """获取字符的显示形式，将控制/空白字符替换为可读标记

        不可见字符直接展示会破坏 UI 布局，故替换为带方括号的缩写：
          - 控制字符 → [NUL], [CR], [LF] 等标准缩写
          - 空格 → [SP]（Space）
          - 不换行空格 → [NBSP]
          - 其他 Cc 类控制字符 → [U+XXXX]
          - 可见字符 → 原样返回
        """
        code = ord(char)
        if code in cls.CONTROL_CHAR_MAP:
            # 标准 C0 控制字符或 DEL，查表取缩写
            return f"[{cls.CONTROL_CHAR_MAP[code]}]"
        if code == 0x20:
            # 普通空格（SP），替换为标记避免混淆
            return "[SP]"
        if code == 0xA0:
            # 不换行空格（NBSP），区分于普通空格
            return "[NBSP]"
        if unicodedata.category(char) == "Cc":
            # 其他控制字符（如 C1 集），用码点标记
            return f"[U+{code:04X}]"
        return char

    @classmethod
    def analyze_character(cls, char, source_encoding="", source_bytes=b"",
                          fallback_encoding=""):
        """分析单个字符在各编码中的十六进制字节表示

        遍历所有支持的编码，对字符执行 encode 操作。
        成功时记录十六进制字节串，失败时标记为 "N/A"。
        Raw Bytes 的选取优先级：原始字节 > 来源编码 > 回退编码。
        """
        result = {
            "Char": cls.get_display_char(char),
            "Unicode": codepoint_display(char),
            "Source Encoding": source_encoding,
        }

        # 逐编码尝试 encode，记录结果或 N/A
        for display_name, std_name in cls.SUPPORTED_ENCODINGS.items():
            try:
                encoded_bytes = char.encode(std_name)
                result[display_name] = bytes_to_hex(encoded_bytes)
            except (UnicodeEncodeError, UnicodeDecodeError):
                # 该字符在当前编码中无法表示（如中文字符在 ASCII 中）
                result[display_name] = "N/A"

        # 决定 "Raw Bytes"（原始字节）的显示值
        if source_bytes:
            # 优先级 1：显式提供的原始字节
            result["Raw Bytes"] = bytes_to_hex(source_bytes)
        elif source_encoding and result.get(source_encoding, "N/A") != "N/A":
            # 优先级 2：从来源编码的 encode 结果中取
            result["Raw Bytes"] = result[source_encoding]
        elif fallback_encoding and result.get(fallback_encoding, "N/A") != "N/A":
            # 优先级 3：来源编码不可用时，用回退编码的 encode 结果
            result["Raw Bytes"] = result[fallback_encoding]
        else:
            # 都无法获取，留空
            result["Raw Bytes"] = ""

        return result

    @classmethod
    def analyze_token(cls, token, fallback_encoding=""):
        """分析一个字符令牌，保留来源编码和原始字节信息

        委托给 analyze_character，传入 token 的 char、来源编码和原始字节。
        """
        return cls.analyze_character(
            token.char,
            source_encoding=token.source_encoding,
            source_bytes=token.source_bytes,
            fallback_encoding=fallback_encoding,
        )

    @classmethod
    def analyze_tokens(cls, tokens, fallback_encoding=""):
        """分析一组字符令牌（保留来源信息）"""
        return [cls.analyze_token(t, fallback_encoding=fallback_encoding) for t in tokens]

    @classmethod
    def get_statistics(cls, results):
        """获取编码支持统计信息

        统计每个编码下有多少字符可以表示（非 N/A），
        以及对应的百分比，用于 UI 中的编码支持率概览。
        """
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
