"""检测器服务 —— 封装编码检测与分词"""

from pathlib import Path

from detector.file_detector import FileEncodingDetector
from services.result import DetectionResult


def diagnose_from_raw(raw_data: bytes, file_path: str | Path):
    """诊断原始字节：返回编码检测结果及各编码解码尝试"""
    trials, enc_name, is_pure_ascii = FileEncodingDetector.diagnose_detect(
        str(file_path), raw_data=raw_data
    )
    return DetectionResult(
        encoding=enc_name,
        std_name=FileEncodingDetector.detect_bytes(raw_data)[1],
        is_pure_ascii=is_pure_ascii,
        trials=trials,
    )


def file_to_tokens(file_path: str | Path, raw_data: bytes | None = None):
    """将文件解码为 CharacterToken 列表"""
    return FileEncodingDetector.file_to_tokens(str(file_path), raw_data=raw_data)


def detect_bytes(raw_data: bytes):
    """仅检测字节序列的编码"""
    enc_name, std_name = FileEncodingDetector.detect_bytes(raw_data)
    return DetectionResult(encoding=enc_name, std_name=std_name)


def charset_detect(raw_data: bytes) -> dict:
    """使用 charset-normalizer 作为交叉参考检测"""
    return FileEncodingDetector.charset_detect(raw_data)
