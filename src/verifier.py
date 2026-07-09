"""
独立验证器 —— 用 Python 标准库验证转换的正确性

不依赖本项目的 EncodingConverter，
避免自我循环验证的陷阱。
"""

from dataclasses import dataclass, field
from typing import Optional

from display_utils import codepoint_display
from encoding import get_std_name


# ---------------------------------------------------------------------------
# 转换验证结果
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 转换验证器
# ---------------------------------------------------------------------------

class ConversionVerifier:
    """验证转换算法是否正确

    用 Python 标准库（str.encode / bytes.decode）做独立验证，
    不调用本项目的 Converter。
    """

    @staticmethod
    def verify_roundtrip(original_tokens, output_path: str,
                         target_encoding: str) -> ConversionVerdict:
        """验证输出文件是否能无损还原为原始字符序列

        流程：
          1. 用 Python 标准库解码输出文件 → 得到字符
          2. 逐字符对比是否与原始 tokens 的字符一致

        返回 ConversionVerdict。
        """
        try:
            with open(output_path, "rb") as f:
                raw = f.read()
        except FileNotFoundError:
            return ConversionVerdict(error=f"Output file not found: {output_path}")

        std_name = get_std_name(target_encoding)

        # 用 Python 标准库验证目标编码有效性
        try:
            recovered_text = raw.decode(std_name)
            is_valid = True
        except UnicodeDecodeError:
            # 输出文件不是合法的目标编码文件
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
                if len(mismatches) < 20:  # 只记录前 20 个
                    mismatches.append({
                        "pos": i,
                        "original": orig,
                        "recovered": recv,
                        "original_cp": codepoint_display(orig),
                        "recovered_cp": codepoint_display(recv),
                    })

        # 长度不一致也记录
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
