"""
编码转换工具函数 —— Token 显示格式化

从 converter_utils.py 拆分后，仅保留 token_target_display。
兼容性扫描相关逻辑移至 compatibility.py。
"""

from display_utils import bytes_to_hex
from encoding import get_std_name


def token_target_display(token) -> str:
    """获取字符转换后的显示字节（十六进制）

    参数 token — 具有 char / target_encoding 属性的对象
    """
    if token.target_encoding:
        std_name = get_std_name(token.target_encoding)
        try:
            encoded = token.char.encode(std_name)
            return bytes_to_hex(encoded)
        except UnicodeEncodeError:
            return "[?]"
    return ""
