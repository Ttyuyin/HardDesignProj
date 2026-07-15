"""兼容性扫描 —— 预览哪些字符在目标编码中不可表示"""

import logging
from dataclasses import dataclass, field

from encoding import get_std_name


logger = logging.getLogger(__name__)


@dataclass
class CompatibilityReport:
    """兼容性扫描报告"""
    total: int = 0
    compatible: int = 0
    problems: list = field(default_factory=list)

    @property
    def rate(self) -> float:
        return (self.compatible / self.total * 100) if self.total else 100.0

    @property
    def problem_count(self) -> int:
        return len(self.problems)


def get_s2t_translator():
    """获取简繁转换器（依赖 opencc-python）"""
    try:
        import opencc
        return opencc.OpenCC('s2t')
    except ImportError:
        logger.warning("opencc-python is not installed. Skipping S2T conversion.")
        return None


def compatibility_scan(tokens, target_encoding: str, s2t_convert: bool = False) -> CompatibilityReport:
    """扫描 token 列表，找出目标编码中不可表示的字符"""
    std_name = get_std_name(target_encoding)
    compatible = 0
    problems = []

    translator = get_s2t_translator() if s2t_convert and target_encoding.upper() in ("BIG5", "BIG5-HKSCS") else None

    for i, token in enumerate(tokens):
        char_to_check = token.char
        if translator:
            char_to_check = translator.convert(char_to_check)
        try:
            char_to_check.encode(std_name)
            compatible += 1
        except UnicodeEncodeError:
            problems.append({
                "char": token.char,
                "unicode": token.unicode_codepoint,
                "position": i,
            })

    return CompatibilityReport(
        total=len(tokens),
        compatible=compatible,
        problems=problems,
    )
