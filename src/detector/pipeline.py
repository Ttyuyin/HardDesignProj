"""
三级编码检测流水线：编排 Layer 1-3，提供公开的 FileEncodingDetector API。

Layer 1（锚点检测）→ Layer 2（Agent 评分）→ Layer 3（决策引擎）。
当锚点层有确定性结果时（如 BOM），直接短路返回，跳过后续层。
"""

import logging
from pathlib import Path

from shared.character_token import CharacterToken
from encoding import DETECTION_ORDER, resolve_std_name

from .anchors import _bom_anchor, _is_pure_ascii_bytes, _utf16_structural_anchor
from .decision import _content_discriminator, _run_agents, _softmax


logger = logging.getLogger(__name__)


def detect_with_full_decision(raw_data: bytes) -> dict:
    """完整三级编码检测流水线：锚点层 → 评分层 → 决策层。

    Args:
        raw_data: 原始字节数据

    Returns:
        dict: 包含最终编码判定结果的字典（encoding、std_name、confidence、top_candidates）
    """
    # 空输入直接返回 UTF-8 默认值
    if not raw_data:
        return {
            "encoding": "UTF-8",
            "std_name": "utf-8",
            "confidence": 1.0,
            "top_candidates": [("UTF-8", 1.0)],
        }

    # ── Layer 1: Anchor Detection（锚点检测）──
    # 确定性的硬规则，无需统计评分

    # 1a. BOM 检测：最优先，有 BOM 即直接返回
    bom_result = _bom_anchor(raw_data)
    if bom_result:
        name, std = bom_result
        return {
            "encoding": name,
            "std_name": std,
            "confidence": 1.0,
            "top_candidates": [(name, 1.0)],
        }

    # 1b. UTF-16 结构锚点：通过 null 字节分布预判字节序
    utf16_anchor = _utf16_structural_anchor(raw_data)

    # 1c. ASCII 短路：纯 ASCII 文件且无 UTF-16 证据时直接返回
    if _is_pure_ascii_bytes(raw_data):
        if utf16_anchor is None:
            return {
                "encoding": "ASCII",
                "std_name": "utf-8",
                "confidence": 1.0,
                "top_candidates": [("ASCII", 1.0)],
            }

    # ── Layer 2: Run All Scoring Agents（运行所有评分 Agent）──
    # 各 Agent 独立评分，返回 0.0 ~ 1.0 的置信度
    scores = _run_agents(raw_data)

    # ── Layer 3: Decision Engine（决策引擎）──

    # 3a. 锚点过滤器：若 Layer 1 检测到 UTF-16 证据，
    #     过滤掉所有非 UTF-16 候选，并对正确字节序施加上提偏置
    if utf16_anchor == "LE":
        scores = {k: v for k, v in scores.items() if k in ("UTF-16 LE", "UTF-16 BE")}
        scores["UTF-16 LE"] = max(scores.get("UTF-16 LE", 0), 0.7)  # LE 上提至 0.7
        scores["UTF-16 BE"] = min(scores.get("UTF-16 BE", 0), 0.3)  # BE 压低至 0.3
    elif utf16_anchor == "BE":
        scores = {k: v for k, v in scores.items() if k in ("UTF-16 LE", "UTF-16 BE")}
        scores["UTF-16 BE"] = max(scores.get("UTF-16 BE", 0), 0.7)  # BE 上提至 0.7
        scores["UTF-16 LE"] = min(scores.get("UTF-16 LE", 0), 0.3)  # LE 压低至 0.3

    # 3b. Softmax 归一化：将各 Agent 的原始分数转换为概率分布
    names = list(scores.keys())
    vals = [scores[n] for n in names]
    probs = _softmax(vals, temperature=10.0)

    ranked = sorted(zip(names, probs), key=lambda x: x[1], reverse=True)

    # 兜底：无任何候选时返回 UTF-8 低置信度
    if not ranked:
        return {
            "encoding": "UTF-8",
            "std_name": "utf-8",
            "confidence": 0.5,
            "top_candidates": [("UTF-8", 0.5)],
        }

    top1_name = ranked[0][0]
    top1_prob = ranked[0][1]
    top2_prob = ranked[1][1] if len(ranked) > 1 else 0.0

    # 3c. 稳定性规则（Stability Rule）
    # 若前两名概率差距 < 5%，认为置信度不足以可靠区分，
    # 则触发平局裁决流程：
    #   1) 收集差距 < 5% 且属于已知编码的候选
    #   2) 若 ≥ 2 个候选平局，使用 _content_discriminator 进行内容特征裁决
    #   3) 若内容裁决无结果，按 DETECTION_ORDER 优先级排序
    #   4) 若仅 1 个候选，直接采用
    #   5) 若不在已知编码中，检查 UTF-8 原始分 > 0.5 则回退到 UTF-8
    gap = top1_prob - top2_prob
    if gap < 0.05 and len(ranked) > 1:
        det_names = {enc.display_name for enc in DETECTION_ORDER}
        tied = [name for name, prob in ranked if top1_prob - prob < 0.05 and name in det_names]

        if len(tied) >= 2:
            # 内容特征裁决：检查解码文本中的特有信号
            winner = _content_discriminator(tied, raw_data)
            if winner:
                top1_name = winner
            else:
                # 按 DETECTION_ORDER 优先级选择第一个匹配项
                for enc in DETECTION_ORDER:
                    if enc.display_name in tied:
                        top1_name = enc.display_name
                        break
        elif len(tied) == 1:
            top1_name = tied[0]
        else:
            # 无匹配已知编码，但 UTF-8 原始分数 > 0.5 时回退
            if scores.get("UTF-8", 0) > 0.5:
                top1_name = "UTF-8"

    std_name = resolve_std_name(top1_name)
    return {
        "encoding": top1_name,
        "std_name": std_name,
        "confidence": round(top1_prob, 4),
        "top_candidates": [(n, round(p, 4)) for n, p in ranked],
    }


# ---------------------------------------------------------------------------
# FileEncodingDetector（公开 API）
# ---------------------------------------------------------------------------

class FileEncodingDetector:
    """文件编码检测器：检测编码并构建每个字符的 CharacterToken。

    提供编码检测、逐 token 解析、诊断调试等功能的统一入口。
    """

    DETECT_ORDER = [(enc.display_name, enc.std_name) for enc in DETECTION_ORDER]

    @classmethod
    def _read_raw(cls, file_path):
        """以二进制模式读取文件原始字节。"""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File does not exist: {file_path}")
        with open(file_path, "rb") as f:
            return f.read()

    @classmethod
    def _detect_from_bytes(cls, raw_data):
        """从原始字节检测编码，返回 (显示名称, 标准名称)。"""
        result = detect_with_full_decision(raw_data)
        return (result["encoding"], result["std_name"])

    @classmethod
    def detect_file(cls, file_path, raw_data=None):
        """检测文件编码，可选传入已读取的 raw_data 避免重复 I/O。"""
        if raw_data is None:
            raw_data = cls._read_raw(file_path)
        if not raw_data:
            return ("UTF-8", "utf-8")
        return cls._detect_from_bytes(raw_data)

    @classmethod
    def detect_bytes(cls, raw_data: bytes) -> tuple[str, str]:
        """从原始字节检测编码，返回 (显示名称, 标准名称)。"""
        return cls._detect_from_bytes(raw_data)

    @classmethod
    def diagnose_detect(cls, file_path, raw_data=None):
        """运行诊断模式：逐一尝试解码并列出结果，辅助调试。

        Returns:
            trials: 每种编码的解码尝试结果列表
            detected_name: 最终检测到的编码名称
            is_pure_ascii: 是否为纯 ASCII 字节
        """
        if raw_data is None:
            raw_data = cls._read_raw(file_path)

        trials = []
        # 诊断项 1：BOM 检测
        bom = _bom_anchor(raw_data)
        if bom:
            trials.append((f"{bom[0]} BOM", raw_data[:3].hex() if raw_data[:3] != b"" else "", "BOM matched"))

        # 诊断项 2：UTF-16 无 BOM 解码尝试
        if len(raw_data) >= 2:
            for label, std in [("UTF-16 (LE, no BOM)", "utf-16-le"),
                               ("UTF-16 (BE, no BOM)", "utf-16-be")]:
                try:
                    raw_data.decode(std)
                    trials.append((label, "", "decoded successfully"))
                except UnicodeDecodeError:
                    trials.append((label, "", "decode failed"))

        # 诊断项 3：DETECTION_ORDER 中各编码逐一尝试
        for display_name, std_name in cls.DETECT_ORDER:
            try:
                raw_data.decode(std_name)
                trials.append((display_name, "", "decoded successfully"))
            except UnicodeDecodeError as e:
                pos = getattr(e, "start", 0)
                sample = raw_data[max(0, pos):pos + 8].hex()
                trials.append((display_name, sample, "decode failed"))
            except LookupError:
                trials.append((display_name, "", "unsupported encoding"))

        result = detect_with_full_decision(raw_data)
        detected_name = result["encoding"]
        is_pure_ascii = _is_pure_ascii_bytes(raw_data)
        return trials, detected_name, is_pure_ascii

    @staticmethod
    def _make_token(char, display_name, file_path, source_bytes):
        """创建单字符的 CharacterToken。"""
        return CharacterToken(
            char=char,
            source_encoding=display_name,
            source_file=str(file_path) if hasattr(file_path, "suffix") else file_path,
            source_bytes=source_bytes,
        )

    @staticmethod
    def charset_detect(raw_data: bytes) -> dict:
        """可选的第三方 charset_normalizer 检测，用于交叉验证。"""
        try:
            import charset_normalizer
            result = charset_normalizer.detect(raw_data)
            return {
                "encoding": result.get("encoding", ""),
                "confidence": result.get("confidence", 0),
            }
        except ImportError:
            return {"encoding": "", "confidence": 0}

    @classmethod
    def file_to_tokens(cls, file_path, raw_data=None):
        """读取文件并返回 CharacterToken 列表，保证字节定位不漂移。

        编码检测后，按编码规则逐个字符解析：
        - 非 UTF-16：使用 surrogateescape 错误处理策略，非法字节映射到 U+DC80-U+DCFF
          区域，保留原始字节信息不丢失
        - UTF-16：使用独立路径（_file_to_tokens_utf16），因为 surrogateescape
          不兼容 UTF-16 编解码器

        BOM 处理：
        - UTF-8 with BOM（utf-8-sig）：跳过前 3 字节 BOM，用 "utf-8" 重新编码
        - UTF-16 with BOM（utf-16）：自动剥离 BOM，用具体字节序编码计算字节长度
        """
        file_path = Path(file_path)
        if raw_data is None:
            raw_data = cls._read_raw(file_path)
        if not raw_data:
            return []

        display_name, std_name = cls.detect_file(file_path, raw_data=raw_data)

        _bom_len = 0
        _reenc = std_name

        # UTF-16 使用独立路径（不兼容 surrogateescape）
        # surrogateescape 在 UTF-16 编解码器中不支持，会抛出 ValueError
        if std_name in ("utf-16", "utf-16-le", "utf-16-be"):
            return cls._file_to_tokens_utf16(raw_data, display_name, std_name, str(file_path))

        # UTF-8 with BOM：解码后切换到纯 UTF-8 重新编码，跳过前 3 字节
        if std_name == "utf-8-sig":
            _reenc = "utf-8"
            _bom_len = 3

        # 使用 surrogateescape 解码，非法字节被映射为 U+DC80-U+DCFF 代理字符
        # 这样可以精确跟踪每个字节到字符的映射关系，保证 byte_pos 不漂移
        text = raw_data.decode(std_name, errors="surrogateescape")

        tokens = []
        byte_pos = _bom_len
        for char in text:
            char_bytes = char.encode(_reenc, errors="surrogateescape")
            source_bytes = raw_data[byte_pos:byte_pos + len(char_bytes)]

            # 代理字符（非法字节）显示为 ?，原始字节保留在 source_bytes 中以备查看
            display_char = "?" if 0xDC00 <= ord(char) <= 0xDCFF else char

            tokens.append(cls._make_token(display_char, display_name, file_path, source_bytes))
            byte_pos += len(char_bytes)

        return tokens

    @classmethod
    def _file_to_tokens_utf16(cls, raw_data, display_name, std_name, file_path):
        """UTF-16 独立 token 生成路径。

        UTF-16 编解码器不支持 surrogateescape 错误处理策略，
        因此必须使用独立实现。使用 errors="replace" 解码，
        并通过原始字节偏移量逐字符解析。

        BOM 处理：
        - "utf-16" 自动识别并剥离 BOM（BOM 不包含在解码后的文本中）
        - 具体字节序编码（utf-16-le/be）不自动剥离 BOM，需手动处理
        """
        _bom_len = 0
        _reenc = std_name
        if std_name == "utf-16":
            # "utf-16" 解码器会自动识别并剥离 BOM，BOM 字节不包含在 text 中
            # 但 raw_data 中 BOM 仍存在，需要手动跳过 BOM 以对齐 byte_pos
            _reenc = "utf-16-le" if raw_data[:2] == b"\xff\xfe" else "utf-16-be"
            _bom_len = 2

        # 使用 std_name（utf-16）解码以自动识别 BOM 并剥离
        text = raw_data.decode(std_name, errors="replace")
        tokens = []
        byte_pos = _bom_len
        for char in text:
            try:
                # 将字符编码回具体字节序以计算字节长度
                char_bytes = char.encode(_reenc)
            except UnicodeEncodeError:
                # 无法编码的字符（如替换字符）按 2 字节步进
                step = 2
                source_bytes = raw_data[byte_pos:byte_pos + step]
                byte_pos += step
                tokens.append(cls._make_token(char, display_name, file_path, source_bytes))
                continue

            source_bytes = raw_data[byte_pos:byte_pos + len(char_bytes)]
            byte_pos += len(char_bytes)
            tokens.append(cls._make_token(char, display_name, file_path, source_bytes))

        return tokens
