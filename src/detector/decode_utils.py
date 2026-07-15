import logging

logger = logging.getLogger(__name__)


def strict_decode(raw_data: bytes, encoding: str) -> str | None:
    """严格解码，解码失败返回 None 而非抛异常"""
    try:
        return raw_data.decode(encoding)
    except (UnicodeDecodeError, LookupError) as e:
        logger.debug("strict_decode failed for %s: %s", encoding, e)
        return None
