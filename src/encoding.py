"""
编码实体与注册中心 —— 项目唯一的编码数据源

定义 Encoding dataclass 和所有受支持编码的注册表。
所有模块从此处获取编码信息，不再定义/引用散装 dict。
单一数据源原则：编码名称、颜色、映射关系均在在此定义。
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Encoding 实体
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Encoding:
    """编码的完整描述

    display_name  — UI 显示名，如 "GBK"
    std_name      — Python 标准库编解码器名，如 "gbk"
    bg_color      — UI 表格中的背景色
    fg_color      — UI 表格中的前景色（文字色）
    """

    display_name: str
    std_name: str
    bg_color: str = "#FFFFFF"
    fg_color: str = "#000000"


# ---------------------------------------------------------------------------
# 编码注册表（唯一数据源）
# ---------------------------------------------------------------------------

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

# 显示名 → Encoding 的快速查找
ENCODING_BY_NAME: dict[str, Encoding] = {e.display_name: e for e in ALL_ENCODINGS}

# 作为列表保留，保持插入顺序
ENCODING_NAMES: list[str] = [e.display_name for e in ALL_ENCODINGS]

# 检测顺序（可被检测的编码，按优先级排列）
# 注意：CJK 多字节编码字节范围高度重叠，无统计分析时存在先天局限
DETECTION_ORDER = [
    ENCODING_BY_NAME["UTF-8"],
    ENCODING_BY_NAME["GBK"],
    ENCODING_BY_NAME["Big5"],
    ENCODING_BY_NAME["Shift-JIS"],
    ENCODING_BY_NAME["GB2312"],
    ENCODING_BY_NAME["Extended ASCII"],
]

# 查看器/分析器中用到的编码列
VIEWER_ENCODING_MAP: dict[str, str] = {
    e.display_name: e.std_name for e in ALL_ENCODINGS
}

# 转换器专用映射（基于 VIEWER_ENCODING_MAP，含覆盖和额外条目）
# GB2312 使用 gbk 编解码器（更兼容）
# UTF-16 作为独立 BOM 条目
CONVERTER_ENCODING_MAP: dict[str, str] = {
    **VIEWER_ENCODING_MAP,
    "GB2312": "gbk",
    "UTF-16": "utf-16",
}

# N/A（不支持）颜色
NA_BG = "#FF6B6B"
NA_FG = "#FFFFFF"


def get_encoding(name: str) -> Encoding:
    """按显示名查找 Encoding，找不到时返回 None"""
    return ENCODING_BY_NAME.get(name)


def get_std_name(name: str) -> str:
    """显示名 → Python 标准库编码名"""
    return VIEWER_ENCODING_MAP.get(name, name)


def resolve_std_name(name: str) -> str:
    if name == "ASCII":
        return "utf-8"
    if name in VIEWER_ENCODING_MAP:
        return VIEWER_ENCODING_MAP[name]
    return name.lower().replace(" ", "-")


def get_bg(name: str) -> str:
    enc = get_encoding(name)
    return enc.bg_color if enc else NA_BG

