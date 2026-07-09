"""
服务层结果类型定义。

GUI 应仅访问这些公开数据类，
不得直接引用 detector / verifier / compatibility 等模块的内部类型。
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DetectionResult:
    """封装的编码检测结果。

    字段说明：
        encoding       — 编码显示名称（例如 "GBK"、"UTF-8"）
        std_name       — Python codec 标准名称（例如 "gbk"、"utf-8"）
        is_pure_ascii  — 是否所有字节均 < 128（纯 ASCII）
        trials         — 诊断列表，元素为 (名称, 十六进制样本, 状态) 元组
                         仅用于状态栏诊断显示
    """
    encoding: str
    std_name: str
    is_pure_ascii: bool = False
    trials: list = field(default_factory=list)


@dataclass
class CompatibilitySummary:
    """兼容性扫描结果 —— 转换前的预览信息。"""
    rate: float = 100.0
    compatible: int = 0
    total: int = 0
    problem_count: int = 0
    problems: list = field(default_factory=list)


@dataclass
class ConversionResult:
    """封装的转换结果。

    GUI 应仅访问这些字段，不得直接操作原始 dict 键
    或 verifier / compatibility 模块的内部对象。
    """
    path: Path
    tokens: list
    total_chars: int
    verified: bool = False
    reversible: bool = False
    all_match: bool = True
    match_count: int = 0
    mismatch_count: int = 0
    mismatch_log: list = field(default_factory=list)
