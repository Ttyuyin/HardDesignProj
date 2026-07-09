"""
检测器服务 —— 封装编码检测与分词功能。

所有公开函数均返回 DetectionResult 或 CharacterToken 列表。
GUI 不应直接导入 detector.pipeline。
本模块是 detector.pipeline.FileEncodingDetector 的外观（Facade）层。
"""

from pathlib import Path

from detector.pipeline import FileEncodingDetector
from services.result import DetectionResult



def diagnose_from_raw(raw_data: bytes, file_path: str | Path):
    """对预处理后的字节数据运行完整诊断。

    封装 FileEncodingDetector.diagnose_detect，返回 DetectionResult（而非原始元组）。
    """
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
    """读取文件并返回 CharacterToken 列表。

    封装 FileEncodingDetector.file_to_tokens。
    """
    return FileEncodingDetector.file_to_tokens(str(file_path), raw_data=raw_data)


def detect_bytes(raw_data: bytes):
    """从原始字节数据检测编码。

    封装 FileEncodingDetector.detect_bytes，返回 DetectionResult。
    """
    enc_name, std_name = FileEncodingDetector.detect_bytes(raw_data)
    return DetectionResult(encoding=enc_name, std_name=std_name)


def charset_detect(raw_data: bytes) -> dict:
    """调用 charset-normalizer 第三方库进行编码检测。

    封装 FileEncodingDetector.charset_detect，返回原始 dict 结果。
    """
    return FileEncodingDetector.charset_detect(raw_data)
