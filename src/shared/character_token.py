"""字符令牌模块 —— 每个字符携带来源编码、目标编码、原始字节等元数据"""

from dataclasses import dataclass

from shared.display_utils import bytes_to_hex, codepoint_display


@dataclass
class CharacterToken:
    """字符令牌，记录字符的编码来源、转换目标及转换信息"""
    char: str
    source_encoding: str = ""
    source_file: str = ""
    source_bytes: bytes = b""
    target_encoding: str = ""

    @property
    def unicode_codepoint(self) -> str:
        """该字符的 Unicode 码点"""
        return codepoint_display(self.char)

    @property
    def source_bytes_hex(self) -> str:
        """原始编码字节的十六进制表示"""
        return bytes_to_hex(self.source_bytes) if self.source_bytes else ""
