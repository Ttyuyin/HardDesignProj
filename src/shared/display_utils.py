def bytes_to_hex(b: bytes) -> str:
    """字节序列转大写十六进制字符串（空格分隔）"""
    return " ".join(f"{b:02X}" for b in b)


def codepoint_display(char: str) -> str:
    """获取字符的 Unicode 码点表示"""
    return f"U+{ord(char):04X}"
