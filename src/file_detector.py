"""
Backward-compatibility re-export stub.

All detection logic has been moved to src/detector/ subpackage.
This module exists only so that existing import paths continue to work.
"""

# Pipeline (public API)
from detector.pipeline import (
    detect_with_full_decision,
    FileEncodingDetector,
)

# Anchors
from detector.anchors import (
    _bom_anchor,
    _is_pure_ascii_bytes,
    _utf16_structural_anchor,
)

# Agents
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

# Decision engine
from detector.decision import (
    _content_discriminator,
    _run_agents,
    _softmax,
)
