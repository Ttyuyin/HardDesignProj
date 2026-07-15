"""转换器服务 —— 封装编码转换与兼容性检查"""

from converter.compatibility import compatibility_scan as _compat_scan
from converter.converter import Converter, convert_file as _convert_file
from services.result import CompatibilitySummary, ConversionResult


supported_encodings = Converter.SUPPORTED_ENCODINGS
error_strategies = Converter.ERROR_STRATEGIES


def get_strategy(display_name: str) -> str:
    """根据 UI 显示名获取错误处理策略"""
    return Converter.ERROR_STRATEGIES.get(display_name, "replace")


def compatibility_scan(tokens, target_encoding: str, s2t_convert: bool = False):
    """扫描字符在目标编码中的兼容性"""
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
    """执行编码转换并返回转换结果"""
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
