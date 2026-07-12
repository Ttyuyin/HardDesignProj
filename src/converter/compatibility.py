"""
兼容性扫描模块 —— 转换前预览哪些字符在目标编码中不可表示

从 converter_utils.py 拆分而来，职责单一。
核心逻辑：对每个字符尝试 encode，捕获 UnicodeEncodeError 即为不兼容。
"""

import logging
from dataclasses import dataclass, field

from encoding import get_std_name


logger = logging.getLogger(__name__)


@dataclass
class CompatibilityReport:
    """兼容性扫描报告 —— 转换前告知用户哪些字符会出问题

    total      — 字符总数
    compatible — 可在目标编码中表示的字符数
    problems   — 无法表示的字符列表，含字符本身、Unicode 码点和位置
    """

    total: int = 0
    compatible: int = 0
    problems: list = field(default_factory=list)
    # problems 中的每个元素: {"char": str, "unicode": str, "position": int}

    @property
    def rate(self) -> float:
        """兼容率（0~100），空文本时返回 100"""
        return (self.compatible / self.total * 100) if self.total else 100.0

    @property
    def problem_count(self) -> int:
        """不兼容字符的数量"""
        return len(self.problems)


def get_s2t_translator():
    """获取简繁转换器，未安装 opencc 时返回 None

    opencc 是可选依赖，不强制安装。
    仅在用户选择简繁转换且目标编码为 Big5 时尝试加载。
    """
    try:
        import opencc
        return opencc.OpenCC('s2t')
    except ImportError:
        logger.warning("opencc-python is not installed. Skipping S2T conversion.")
        return None


def compatibility_scan(tokens, target_encoding: str, s2t_convert: bool = False) -> CompatibilityReport:
    """扫描一组 token 在目标编码中的兼容性

    参数:
        tokens           — CharacterToken 列表
        target_encoding  — 目标编码显示名（如 "GBK"）
        s2t_convert      — 是否先做简繁转换再检查（用于 Big5 目标）

    流程：对每个字符尝试 encode → 成功则兼容，失败则记录到 problems。
    返回 CompatibilityReport，UI 层据此展示预览警告。

    返回 CompatibilityReport。
    """
    std_name = get_std_name(target_encoding)
    compatible = 0
    problems = []

    # 仅当目标编码为 Big5 且用户选择简繁转换时加载转换器
    translator = get_s2t_translator() if s2t_convert and target_encoding.upper() in ("BIG5", "BIG5-HKSCS") else None

    for i, token in enumerate(tokens):
        char_to_check = token.char
        if translator:
            # 先简繁转换，再用转换后的字符检查兼容性
            char_to_check = translator.convert(char_to_check)
        try:
            char_to_check.encode(std_name)
            compatible += 1
        except UnicodeEncodeError:
            # 该字符在目标编码中无法表示，记录问题
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
