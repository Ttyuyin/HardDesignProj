"""
Service-layer result types.

GUI should only access these public dataclasses,
never internal types from detector / verifier / compatibility modules.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DetectionResult:
    """Encapsulated detection result.

    Fields:
        encoding     — display name (e.g. "GBK", "UTF-8")
        std_name     — Python codec name (e.g. "gbk", "utf-8")
        is_pure_ascii — True if all bytes < 128
        trials       — diagnostic list of (name, hex_sample, status) tuples
                       (used only for status-bar diagnostic display)
    """
    encoding: str
    std_name: str
    is_pure_ascii: bool = False
    trials: list = field(default_factory=list)


@dataclass
class CompatibilitySummary:
    """Compatibility scan result — pre-conversion preview."""
    rate: float = 100.0
    compatible: int = 0
    total: int = 0
    problem_count: int = 0
    problems: list = field(default_factory=list)


@dataclass
class ConversionResult:
    """Encapsulated conversion result.

    GUI should access only these fields — never raw dict keys
    or internal objects from verifier / compatibility modules.
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
