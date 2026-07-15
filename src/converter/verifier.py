"""独立验证器 —— 用 Python 标准库验证转换正确性"""

from dataclasses import dataclass, field
from typing import Optional

from shared.display_utils import codepoint_display
from encoding import get_std_name


@dataclass
class ConversionVerdict:
    """单次转换验证的结果"""
    total_chars: int = 0
    match_count: int = 0
    mismatch_count: int = 0
    is_valid_target_encoding: bool = False
    mismatches: list = field(default_factory=list)
    error: Optional[str] = None

    @property
    def all_match(self) -> bool:
        return self.match_count == self.total_chars > 0


class ConversionVerifier:

    @staticmethod
    def verify_roundtrip(original_tokens, output_path: str,
                         target_encoding: str) -> ConversionVerdict:
        """回环验证：解码输出文件并与原始字符逐位比对"""
        try:
            with open(output_path, "rb") as f:
                raw = f.read()
        except FileNotFoundError:
            return ConversionVerdict(error=f"Output file not found: {output_path}")

        std_name = get_std_name(target_encoding)

        try:
            recovered_text = raw.decode(std_name)
            is_valid = True
        except UnicodeDecodeError:
            return ConversionVerdict(
                is_valid_target_encoding=False,
                error=(
                    f"Output file is NOT a valid {target_encoding} file. "
                    f"Decode failed at byte position."
                ),
            )

        original_text = "".join(t.char for t in original_tokens)
        mismatches = []
        match_count = 0
        mismatch_count = 0

        for i, (orig, recv) in enumerate(zip(original_text, recovered_text)):
            if orig == recv:
                match_count += 1
            else:
                mismatch_count += 1
                if len(mismatches) < 20:
                    mismatches.append({
                        "pos": i,
                        "original": orig,
                        "recovered": recv,
                        "original_cp": codepoint_display(orig),
                        "recovered_cp": codepoint_display(recv),
                    })

        len_diff = len(original_text) - len(recovered_text)
        if len_diff != 0:
            note = (
                f"Length mismatch: original={len(original_text)}, "
                f"recovered={len(recovered_text)}"
            )
            if len(mismatches) < 20:
                mismatches.append({"note": note})

        return ConversionVerdict(
            total_chars=max(len(original_text), len(recovered_text)),
            match_count=match_count,
            mismatch_count=mismatch_count,
            is_valid_target_encoding=is_valid,
            mismatches=mismatches,
        )
