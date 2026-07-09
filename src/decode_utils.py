"""
Decoding utilities — centralized try/except decode logic.

Extracted from file_detector.py to eliminate repeated
try/decode/except patterns across all agents.
"""

import logging

logger = logging.getLogger(__name__)


def strict_decode(raw_data: bytes, encoding: str) -> str | None:
    """Attempt strict decoding of raw_data with the given encoding.

    Returns the decoded text on success, None on failure.
    """
    try:
        return raw_data.decode(encoding)
    except (UnicodeDecodeError, LookupError) as e:
        logger.debug("strict_decode failed for %s: %s", encoding, e)
        return None
