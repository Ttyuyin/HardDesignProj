"""
Detector service — encapsulates encoding detection & tokenization.

All public functions return DetectionResult or CharacterToken list.
GUI should never import detector.pipeline directly.
"""

from pathlib import Path

from detector.pipeline import FileEncodingDetector
from services.result import DetectionResult



def diagnose_from_raw(raw_data: bytes, file_path: str | Path):
    """Run full diagnostics on pre-loaded bytes.

    Returns DetectionResult.
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
    """Read file and return CharacterToken list."""
    return FileEncodingDetector.file_to_tokens(str(file_path), raw_data=raw_data)


def detect_bytes(raw_data: bytes):
    """Detect encoding from raw bytes. Returns DetectionResult."""
    enc_name, std_name = FileEncodingDetector.detect_bytes(raw_data)
    return DetectionResult(encoding=enc_name, std_name=std_name)


def charset_detect(raw_data: bytes) -> dict:
    """Run charset-normalizer detection (third-party). Returns dict."""
    return FileEncodingDetector.charset_detect(raw_data)
