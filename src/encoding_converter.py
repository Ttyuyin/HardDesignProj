"""Encoding conversion helpers — pure logic separated from file I/O."""

from pathlib import Path
import logging

from compatibility import get_s2t_translator
from encoding import CONVERTER_ENCODING_MAP
from verifier import ConversionVerifier


logger = logging.getLogger(__name__)


class Converter:
    """编码转换器 —— 纯逻辑，从 encoding.py 注册表自动构建编码列表"""

    # 从 encoding.py 获取统一映射（唯一数据源）
    SUPPORTED_ENCODINGS = CONVERTER_ENCODING_MAP

    ERROR_STRATEGIES = {
        "Replace (Auto)": "replace",  # 极简智能替换
        "Strict": "strict",           # 严格报错
    }

    DEFAULT_OUTPUT_DIR = Path(__file__).parent / "output" / "converted"

    @staticmethod
    def _safe_name(name):
        return name.replace(" ", "_").replace("-", "").lower()

    @classmethod
    def _encode(cls, char, std_name, error_strategy):
        """对单个字符执行编码（物理对齐硬化防线）"""
        try:
            return char.encode(std_name)
        except UnicodeEncodeError:
            # 1. 严格模式：直接抛出异常
            if error_strategy == "strict":
                raise ValueError(
                    f"Encoding failed ({std_name}): {char} (U+{ord(char):04X})"
                )

            # 2. 动态半角替换策略（针对 1 字节编码和 UTF-16）
            try:
                encoded_bytes = "?".encode(std_name)
            except UnicodeEncodeError:
                encoded_bytes = b"?"

            # 3. 万无一失物理安全屏障：针对 UTF-16 目标，强制进行 2 字节整倍数对齐校验
            if std_name.startswith("utf-16"):
                if len(encoded_bytes) % 2 != 0:
                    # 发生未知错误导致产生了奇数个字节时，强制修正为 UTF-16 下合法的双字节 "?"
                    encoded_bytes = b"?\x00" if std_name == "utf-16-le" else b"\x00?"

            return encoded_bytes

    @classmethod
    def convert_tokens(cls, tokens, target_encoding, error_strategy="replace_full", s2t_convert=False):
        """将一组 CharacterToken 按目标编码转换"""
        tgt_std = cls.SUPPORTED_ENCODINGS.get(target_encoding, "utf-8")
        output_parts = []

        translator = get_s2t_translator() if s2t_convert and target_encoding.upper() in ("BIG5", "BIG5-HKSCS") else None

        for token in tokens:
            token.target_encoding = target_encoding
            
            char_to_encode = token.char
            if translator and char_to_encode:
                char_to_encode = translator.convert(char_to_encode)

            encoded = cls._encode(char_to_encode, tgt_std, error_strategy)
            output_parts.append(encoded)

        return b"".join(output_parts), tokens

    @staticmethod
    def _output_path(source_path, source_encoding, target_encoding, output_dir=None):
        """生成输出文件路径"""
        if output_dir is None:
            output_dir = Converter.DEFAULT_OUTPUT_DIR
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(source_path).stem
        suffix = Path(source_path).suffix or ".txt"
        safe_src = Converter._safe_name(source_encoding)
        safe_tgt = Converter._safe_name(target_encoding)
        return output_dir / f"{stem}_{safe_src}_to_{safe_tgt}{suffix}"



# ---------------------------------------------------------------------------
# 高层编排函数
# ---------------------------------------------------------------------------

def convert_file(source_path, tokens, source_encoding,
                 target_encoding, output_dir=None, error_strategy="replace_full", s2t_convert=False):
    """对已解码的 tokens 执行转换并写出文件"""
    source_path = Path(source_path)

    output_bytes, processed_tokens = Converter.convert_tokens(
        tokens, target_encoding, error_strategy, s2t_convert=s2t_convert
    )

    output_path = Converter._output_path(
        source_path, source_encoding, target_encoding, output_dir
    )
    with open(output_path, "wb") as f:
        f.write(output_bytes)

    # 验证目标编码的合法性与往返一致性
    verdict = ConversionVerifier.verify_roundtrip(
        processed_tokens, str(output_path), target_encoding
    )
    verified = verdict.is_valid_target_encoding
    reversible = verdict.all_match and not verdict.error

    log_suffix = []
    if verified:
        log_suffix.append(
            f"verified: {'reversible' if reversible else 'not reversible'}"
        )
    suffix = f" ({' | '.join(log_suffix)})" if log_suffix else ""
    logger.info(
        "Conversion successful: %s -> %s (%s)%s",
        source_path.name, output_path.name, target_encoding, suffix,
    )

    return {
        "path": output_path,
        "total_chars": len(processed_tokens),
        "tokens": processed_tokens,
        "verified": verified,
        "reversible": reversible,
        "verdict": verdict,
    }