"""服务层结果类型定义。GUI 应仅访问这些公开数据类。"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DetectionResult:
    encoding: str
    std_name: str
    is_pure_ascii: bool = False
    trials: list = field(default_factory=list)


@dataclass
class CompatibilitySummary:
    rate: float = 100.0
    compatible: int = 0
    total: int = 0
    problem_count: int = 0
    problems: list = field(default_factory=list)


@dataclass
class ConversionResult:
    path: Path
    tokens: list
    total_chars: int
    verified: bool = False
    reversible: bool = False
    all_match: bool = True
    match_count: int = 0
    mismatch_count: int = 0
    mismatch_log: list = field(default_factory=list)
