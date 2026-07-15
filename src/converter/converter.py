"""编码转换核心逻辑 —— Converter 类 + convert_file 编排函数"""

from pathlib import Path
import logging

from converter.compatibility import get_s2t_translator
from encoding import CONVERTER_ENCODING_MAP
from converter.verifier import ConversionVerifier


logger = logging.getLogger(__name__)


class Converter:

    SUPPORTED_ENCODINGS = CONVERTER_ENCODING_MAP

    ERROR_STRATEGIES = {
        "Replace (Auto)": "replace",
        "Strict": "strict",
    }

    DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "converted"

    @staticmethod
    def _safe_name(name):
        """将编码名转为安全文件名"""
        return name.replace(" ", "_").replace("-", "").lower()

    @classmethod
    def _encode(cls, char, std_name, error_strategy):
        """将单个字符编码为目标编码字节；严格模式失败时抛异常"""
        try:
            return char.encode(std_name)
        except UnicodeEncodeError:
            if error_strategy == "strict":
                raise ValueError(
                    f"Encoding failed ({std_name}): {char} (U+{ord(char):04X})"
                )

            try:
                encoded_bytes = "?".encode(std_name)
            except UnicodeEncodeError:
                encoded_bytes = b"?"

            if std_name.startswith("utf-16"):
                if len(encoded_bytes) % 2 != 0:
                    encoded_bytes = b"?\x00" if std_name.endswith("-le") else b"\x00?"

            return encoded_bytes

    @classmethod
    def convert_tokens(cls, tokens, target_encoding, error_strategy="replace_full", s2t_convert=False):
        """将 token 列表逐字符转换为目标编码"""
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
        """生成转换输出文件的完整路径"""
        if output_dir is None:
            output_dir = Converter.DEFAULT_OUTPUT_DIR
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(source_path).stem
        suffix = Path(source_path).suffix or ".txt"
        safe_src = Converter._safe_name(source_encoding)
        safe_tgt = Converter._safe_name(target_encoding)
        return output_dir / f"{stem}_{safe_src}_to_{safe_tgt}{suffix}"


def convert_file(source_path, tokens, source_encoding,
                 target_encoding, output_dir=None, error_strategy="replace_full", s2t_convert=False):
    """完整转换流程：转换 token → 写文件 → 回环验证"""
    source_path = Path(source_path)

    output_bytes, processed_tokens = Converter.convert_tokens(
        tokens, target_encoding, error_strategy, s2t_convert=s2t_convert
    )

    output_path = Converter._output_path(
        source_path, source_encoding, target_encoding, output_dir
    )
    with open(output_path, "wb") as f:
        f.write(output_bytes)

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
