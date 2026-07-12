"""
解码工具函数 —— 统一的 try/except 解码逻辑

从 file_detector.py 提取，消除各模块中重复的 try/decode/except 模式。
单一职责：封装解码异常处理，让调用方无需关心细节。
"""

import logging

logger = logging.getLogger(__name__)


def strict_decode(raw_data: bytes, encoding: str) -> str | None:
    """对原始字节执行严格解码

    用指定编码尝试解码，成功返回文本，失败返回 None。
    所有解码异常（编码不存在、字节非法等）在此统一捕获，
    避免调用方层层处理异常。
    """
    try:
        return raw_data.decode(encoding)
    except (UnicodeDecodeError, LookupError) as e:
        logger.debug("strict_decode failed for %s: %s", encoding, e)
        return None
