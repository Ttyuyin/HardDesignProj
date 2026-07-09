"""
编码转换核心逻辑 —— 纯逻辑层，与文件 I/O 分离

提供 Converter 类和顶层 convert_file 编排函数。
不直接处理用户界面或文件选择，由上层模块（如 converter_tab.py）调用。
"""

from pathlib import Path
import logging

from compatibility import get_s2t_translator
from encoding import CONVERTER_ENCODING_MAP
from verifier import ConversionVerifier


logger = logging.getLogger(__name__)


class Converter:
    """编码转换器 —— 纯逻辑，从 encoding.py 注册表自动构建编码列表

    核心职责：将 CharacterToken 序列按目标编码转换为字节流。
    支持错误策略（替换/严格）和可选的简繁转换预处理。
    """

    # 从 encoding.py 获取统一映射（唯一数据源）
    SUPPORTED_ENCODINGS = CONVERTER_ENCODING_MAP

    ERROR_STRATEGIES = {
        "Replace (Auto)": "replace",  # 极简智能替换：不可编码字符替换为 "?"
        "Strict": "strict",           # 严格报错：遇到不可编码字符立即抛出异常
    }

    DEFAULT_OUTPUT_DIR = Path(__file__).parent / "output" / "converted"

    @staticmethod
    def _safe_name(name):
        """将编码名转换为安全的文件名字段格式"""
        return name.replace(" ", "_").replace("-", "").lower()

    @classmethod
    def _encode(cls, char, std_name, error_strategy):
        """对单个字符执行编码（含多层容错防线）

        第 1 层：直接 encode，成功则直接返回。
        第 2 层：UnicodeEncodeError 时根据策略处理：
          - 严格模式：抛出异常
          - 替换模式：用 "?" 字符的编码字节替代
        第 3 层（物理对齐硬化防线）：UTF-16 目标下确保字节数为偶数。
          这是防御性编程 —— 即使 "?" 的编码出现异常奇数长度，
          也强制补齐以保证输出的 UTF-16 字节流合法。
        """
        try:
            return char.encode(std_name)
        except UnicodeEncodeError:
            # 第 1 道防线：严格模式直接报错，不给静默数据损坏的机会
            if error_strategy == "strict":
                raise ValueError(
                    f"Encoding failed ({std_name}): {char} (U+{ord(char):04X})"
                )

            # 第 2 道防线：动态半角替换策略
            # 用 "?" 字符在目标编码中的实际编码字节作为替换值
            try:
                encoded_bytes = "?".encode(std_name)
            except UnicodeEncodeError:
                # 极端情况：目标编码不包含 "?" 时，回退到纯 ASCII 问号
                encoded_bytes = b"?"

            # 第 3 道防线：万无一失物理安全屏障
            # 针对 UTF-16 目标，强制进行 2 字节整倍数对齐校验
            # UTF-16 要求数据长度为 2 的倍数，奇数长度会导致解码失败
            if std_name.startswith("utf-16"):
                if len(encoded_bytes) % 2 != 0:
                    # 发生未知错误导致产生了奇数个字节时，强制修正为 UTF-16 下合法的双字节 "?"
                    encoded_bytes = b"?\x00" if std_name == "utf-16-le" else b"\x00?"

            return encoded_bytes

    @classmethod
    def convert_tokens(cls, tokens, target_encoding, error_strategy="replace_full", s2t_convert=False):
        """将一组 CharacterToken 按目标编码转换

        遍历 token 列表，对每个字符执行 _encode 并收集结果字节。
        同时为每个 token 设置 target_encoding 字段，供后续 UI 显示使用。

        参数:
          tokens           — CharacterToken 列表
          target_encoding  — 目标编码显示名（如 "GBK"）
          error_strategy   — 错误处理策略
          s2t_convert      — 是否对 Big5 目标执行简繁转换

        返回 (合并后的字节流, 更新后的 tokens)
        """
        tgt_std = cls.SUPPORTED_ENCODINGS.get(target_encoding, "utf-8")
        output_parts = []

        # 仅 Big5 目标下且用户选择时才加载简繁转换器
        translator = get_s2t_translator() if s2t_convert and target_encoding.upper() in ("BIG5", "BIG5-HKSCS") else None

        for token in tokens:
            token.target_encoding = target_encoding
            
            char_to_encode = token.char
            if translator and char_to_encode:
                # 在编码前先做简繁转换：简体 → 繁体
                char_to_encode = translator.convert(char_to_encode)

            encoded = cls._encode(char_to_encode, tgt_std, error_strategy)
            output_parts.append(encoded)

        return b"".join(output_parts), tokens

    @staticmethod
    def _output_path(source_path, source_encoding, target_encoding, output_dir=None):
        """生成输出文件路径

        格式: {原文件名}_{源编码}_to_{目标编码}{后缀}
        确保输出目录存在（自动创建）。
        """
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
    """对已解码的 tokens 执行转换并写出文件

    完整流程：
      1. 调用 Converter.convert_tokens 执行编码转换
      2. 生成输出文件路径并写出字节流
      3. 用 ConversionVerifier 验证输出文件合法性和往返一致性
      4. 记录日志并返回结果字典

    返回包含路径、token 列表、验证结果的字典。
    """
    source_path = Path(source_path)

    # 执行核心转换
    output_bytes, processed_tokens = Converter.convert_tokens(
        tokens, target_encoding, error_strategy, s2t_convert=s2t_convert
    )

    # 生成输出路径并写出文件
    output_path = Converter._output_path(
        source_path, source_encoding, target_encoding, output_dir
    )
    with open(output_path, "wb") as f:
        f.write(output_bytes)

    # 验证目标编码的合法性与往返一致性
    # 使用独立于 Converter 的 Python 标准库做验证
    verdict = ConversionVerifier.verify_roundtrip(
        processed_tokens, str(output_path), target_encoding
    )
    verified = verdict.is_valid_target_encoding
    reversible = verdict.all_match and not verdict.error

    # 构造日志后缀
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