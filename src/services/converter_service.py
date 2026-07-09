"""
Converter service — encapsulates encoding conversion & compatibility.

All public functions return ConversionResult / CompatibilitySummary.
GUI should never import encoding_converter or compatibility directly.
"""

from compatibility import compatibility_scan as _compat_scan
from encoding_converter import Converter, convert_file as _convert_file
from services.result import CompatibilitySummary, ConversionResult


# Re-export encoding/strategy registries
supported_encodings = Converter.SUPPORTED_ENCODINGS
error_strategies = Converter.ERROR_STRATEGIES


def get_strategy(display_name: str) -> str:
    """Map display name to codec error strategy string."""
    return Converter.ERROR_STRATEGIES.get(display_name, "replace")


def compatibility_scan(tokens, target_encoding: str, s2t_convert: bool = False):
    """Scan tokens for characters not representable in target encoding.

    Returns CompatibilitySummary (not internal CompatibilityReport).
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
    """Convert file from source to target encoding.

    Returns ConversionResult (not raw dict).
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
