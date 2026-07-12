"""
转换器服务 —— 封装编码转换与兼容性检查功能。

所有公开函数均返回 ConversionResult 或 CompatibilitySummary。
GUI 不应直接导入 encoding_converter 或 compatibility 模块。
本模块负责将内部原始类型（raw dict、内部 Report 对象）转换为服务层公开类型。
"""

from converter.compatibility import compatibility_scan as _compat_scan
from converter.converter import Converter, convert_file as _convert_file
from services.result import CompatibilitySummary, ConversionResult


# 重新导出编码与错误策略注册表，供 GUI 下拉菜单等消费方使用
supported_encodings = Converter.SUPPORTED_ENCODINGS
error_strategies = Converter.ERROR_STRATEGIES


def get_strategy(display_name: str) -> str:
    """将界面显示名称映射为 Python codec 错误策略字符串。"""
    return Converter.ERROR_STRATEGIES.get(display_name, "replace")


def compatibility_scan(tokens, target_encoding: str, s2t_convert: bool = False):
    """扫描 tokens 中在目标编码下无法表示的字符（兼容性检查）。

    包装 internal compatibility_scan，将内部 CompatibilityReport 转换为公开的 CompatibilitySummary。
    """
    report = _compat_scan(tokens, target_encoding, s2t_convert=s2t_convert)
    return CompatibilitySummary(
        rate=report.rate,
        compatible=report.compatible,
        total=report.total,
        problem_count=report.problem_count,
        problems=report.problems,
    )


def convert_file(
    source_path, tokens, src_enc, tgt_enc, output_dir,
    strategy="replace_full", s2t_convert=False,
):
    """将文件从源编码转换为目标编码。

    包装内部 _convert_file，将原始 dict 结果转换为公开的 ConversionResult；
    同时从 verdict 中提取校验信息并格式化为可读的 mismatch_log。
    """
    raw = _convert_file(
        source_path, tokens, src_enc, tgt_enc,
        output_dir, strategy, s2t_convert=s2t_convert,
    )
    verdict = raw.get("verdict")
    mismatch_log = []
    if verdict and not verdict.all_match:
        mismatch_log.append(
            f"Verifier: {verdict.match_count}/{verdict.total_chars} match"
        )
        for m in verdict.mismatches[:5]:
            if "note" in m:
                mismatch_log.append(f"  {m['note']}")
            else:
                mismatch_log.append(
                    f"  Pos {m['pos']}: {m['original']}({m['original_cp']})"
                    f" -> {m['recovered']}({m['recovered_cp']})"
                )
    return ConversionResult(
        path=raw["path"],
        tokens=raw["tokens"],
        total_chars=raw["total_chars"],
        verified=raw.get("verified", False),
        reversible=raw.get("reversible", False),
        all_match=verdict.all_match if verdict else True,
        match_count=verdict.match_count if verdict else 0,
        mismatch_count=verdict.mismatch_count if verdict else 0,
        mismatch_log=mismatch_log,
    )
