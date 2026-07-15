from shared.display_utils import bytes_to_hex
from encoding import get_std_name


def token_target_display(token) -> str:
    """获取 token 在目标编码下的十六进制显示"""
    if token.target_encoding:
        std_name = get_std_name(token.target_encoding)
        try:
            encoded = token.char.encode(std_name)
            return bytes_to_hex(encoded)
        except UnicodeEncodeError:
            return "[?]"
    return ""
