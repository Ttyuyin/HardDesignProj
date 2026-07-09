"""
向后兼容的重新导出桩模块。

所有检测逻辑已迁移至 src/detector/ 子包。
本模块仅用于保证旧导入路径（如 from file_detector import FileEncodingDetector）仍然可用。
"""

# 管道 —— 公开 API
from detector.pipeline import (
    detect_with_full_decision,
    FileEncodingDetector,
)

# 锚点 —— BOM 检测 / 纯 ASCII 判断 / UTF-16 结构探测
from detector.anchors import (
    _bom_anchor,
    _is_pure_ascii_bytes,
    _utf16_structural_anchor,
)

# 检测代理 —— 各编码专有检测器
from detector.agents import (
    _ALL_AGENTS,
    _extended_ascii_agent,
    _make_utf16_agent,
    _utf8_agent,
    _utf16le_agent,
    _utf16be_agent,
    EncodingDetectionAgent,
    GBK_AGENT,
    BIG5_AGENT,
    SHIFT_JIS_AGENT,
)

# 决策引擎 —— 内容判别 / 代理调度 / 置信度归一化
from detector.decision import (
    _content_discriminator,
    _run_agents,
    _softmax,
)
