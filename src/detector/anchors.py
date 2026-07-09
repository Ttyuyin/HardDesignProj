"""
Layer 1: Anchor Detector（硬规则锚点检测）

BOM 检测、纯 ASCII 快速判定、UTF-16 结构启发式判定。
作为三级流水线的第一层，提供无需统计分析即可确定的编码证据。
"""


def _bom_anchor(raw_data: bytes) -> tuple[str, str] | None:
    """检查字节序标记（BOM），返回 (显示名称, 标准名称) 或 None。

    BOM 是文件开头的特殊字节序列，用于标识编码方式和字节序。
    - UTF-8    BOM: EF BB BF
    - UTF-16 LE BOM: FF FE
    - UTF-16 BE BOM: FE FF
    """
    if raw_data[:3] == b"\xef\xbb\xbf":
        return ("UTF-8", "utf-8-sig")        # UTF-8 with BOM（含签名）
    if raw_data[:2] == b"\xff\xfe":
        return ("UTF-16 LE", "utf-16")        # UTF-16 小端序
    if raw_data[:2] == b"\xfe\xff":
        return ("UTF-16 BE", "utf-16")        # UTF-16 大端序
    return None


def _is_pure_ascii_bytes(raw_data: bytes) -> bool:
    """判断是否为纯 ASCII 字节（所有字节 < 128）。

    纯 ASCII 文件无需进入后续 CJK 编码分析，可直接短路返回。
    """
    return all(b < 128 for b in raw_data)


def _utf16_structural_anchor(raw_data: bytes) -> str | None:
    """通过 null 字节分布比率判断 UTF-16 字节序。

    核心逻辑：UTF-16 中每个码元为 2 字节，ASCII 字符的高位字节通常为 0x00。
    若偶数位（BE 编码的数据位）或奇数位（LE 编码的数据位）的 0x00 比例 > 25%，
    则判定为对应字节序。
    """
    length = len(raw_data)
    if length < 2:
        return None
    usable_len = length - 1 if length % 2 != 0 else length  # 截断奇数长度
    half = usable_len // 2                                   # UTF-16 码元数量
    even_nulls = sum(1 for i in range(0, usable_len, 2) if raw_data[i] == 0)
    odd_nulls = sum(1 for i in range(1, usable_len, 2) if raw_data[i] == 0)
    even_ratio = even_nulls / half
    odd_ratio = odd_nulls / half
    # 偶数位 0x00 密集 => 大端序（数据在高字节）
    if even_ratio > 0.25:
        return "BE"
    # 奇数位 0x00 密集 => 小端序（数据在低字节）
    if odd_ratio > 0.25:
        return "LE"
    return None
