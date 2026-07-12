"""
显示格式化工具 —— 字节十六进制 / Unicode 码点字符串

bytes_to_hex     — 将字节序列格式化为空格分隔的十六进制串
codepoint_display — 将字符格式化为 "U+XXXX" 标准码点表示
"""


def bytes_to_hex(b: bytes) -> str:
    """将字节数组转换为十六进制显示字符串（空格分隔）

    例如: b'\\x48\\x65' → "48 65"
    用于在 UI 中直观展示编码后的字节序列
    """
    return " ".join(f"{b:02X}" for b in b)


def codepoint_display(char: str) -> str:
    """将单个字符转换为 Unicode 码点显示格式

    例如: 'A' → "U+0041"，'中' → "U+4E2D"
    提供标准化的码点标识，便于跨编码的字符溯源
    """
    return f"U+{ord(char):04X}"
