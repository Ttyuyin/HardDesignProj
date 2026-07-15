"""
编码实体与注册中心 —— 项目唯一的编码数据源
定义 Encoding dataclass 和所有受支持编码的注册表。
所有模块从此处获取编码信息，不再定义/引用散装 dict。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Encoding:
    """编码的完整描述：UI 显示名、Python 标准库编解码器名、UI 背景/前景色"""

    display_name: str
    std_name: str
    bg_color: str = "#FFFFFF"
    fg_color: str = "#000000"


ALL_ENCODINGS = [
    Encoding("ASCII",          "ascii",        "#90EE90", "#000000"),
    Encoding("Extended ASCII", "cp1252",       "#ADD8E6", "#000000"),
    Encoding("Shift-JIS",      "cp932",         "#E6E6FA", "#000000"),
    Encoding("GB2312",         "gb2312",       "#FFFACD", "#000000"),
    Encoding("GBK",            "gbk",          "#FFB347", "#000000"),
    Encoding("Big5",           "big5",         "#FFB6C1", "#000000"),
    Encoding("UTF-8",          "utf-8",        "#DDA0DD", "#000000"),
    Encoding("UTF-16 LE",      "utf-16-le",    "#D3D3D3", "#000000"),
    Encoding("UTF-16 BE",      "utf-16-be",    "#C8C8C8", "#000000"),
]

ENCODING_BY_NAME: dict[str, Encoding] = {e.display_name: e for e in ALL_ENCODINGS}
ENCODING_NAMES: list[str] = [e.display_name for e in ALL_ENCODINGS]

DETECTION_ORDER = [
    ENCODING_BY_NAME["UTF-8"],
    ENCODING_BY_NAME["GBK"],
    ENCODING_BY_NAME["Big5"],
    ENCODING_BY_NAME["Shift-JIS"],
    ENCODING_BY_NAME["GB2312"],
    ENCODING_BY_NAME["Extended ASCII"],
]

VIEWER_ENCODING_MAP: dict[str, str] = {
    e.display_name: e.std_name for e in ALL_ENCODINGS
}

CONVERTER_ENCODING_MAP: dict[str, str] = {
    **VIEWER_ENCODING_MAP,
    "GB2312": "gbk",
}

NA_BG = "#FF6B6B"
NA_FG = "#FFFFFF"


def get_encoding(name: str) -> Encoding:
    """根据显示名获取编码对象"""
    return ENCODING_BY_NAME.get(name)


def get_std_name(name: str) -> str:
    """获取编码显示名对应的 Python 编解码器名"""
    return VIEWER_ENCODING_MAP.get(name, name)


def resolve_std_name(name: str) -> str:
    """将显示名解析为标准库编解码器名，ASCII 特殊处理为 utf-8"""
    if name == "ASCII":
        return "utf-8"
    if name in VIEWER_ENCODING_MAP:
        return VIEWER_ENCODING_MAP[name]
    return name.lower().replace(" ", "-")


def get_bg(name: str) -> str:
    """获取编码在 UI 中对应的背景色"""
    enc = get_encoding(name)
    return enc.bg_color if enc else NA_BG
