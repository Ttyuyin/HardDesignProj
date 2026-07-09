"""
字符令牌模块
每个字符携带来源编码、目标编码、原始字节等元数据，
确保编码转换全程可追溯
"""

from dataclasses import dataclass

from display_utils import bytes_to_hex, codepoint_display


@dataclass
class CharacterToken:
    """字符令牌，记录字符的编码来源、转换目标及转换信息

    类似护照：不只记录"你是谁"（字符本身），
    还记录"你从哪来"（来源编码、原始字节）
    和"你要去哪"（目标编码）

    显示逻辑见 converter_utils.token_target_display()
    """
    char: str
    source_encoding: str = ""
    source_file: str = ""
    source_bytes: bytes = b""
    target_encoding: str = ""

    @property
    def unicode_codepoint(self) -> str:
        return codepoint_display(self.char)

    @property
    def source_bytes_hex(self) -> str:
        return bytes_to_hex(self.source_bytes) if self.source_bytes else ""
