"""File-oriented facade for the byte-level encoding detection pipeline."""

from pathlib import Path

from .diagnostics import diagnose_bytes
from .tokenizer import tokens_from_bytes


class FileEncodingDetector:
    """文件读取、诊断、分词的 Facade"""

    @staticmethod
    def _read_raw(file_path: str | Path) -> bytes:
        """以二进制模式读取文件全部内容"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {path}")
        with open(path, "rb") as file:
            return file.read()

    @staticmethod
    def _detect_from_bytes(raw_data: bytes) -> tuple[str, str]:
        """对字节序列执行完整检测流水线"""
        from .pipeline import detect_with_full_decision

        result = detect_with_full_decision(raw_data)
        return result["encoding"], result["std_name"]

    @classmethod
    def detect_file(
        cls,
        file_path: str | Path,
        raw_data: bytes | None = None,
    ) -> tuple[str, str]:
        """检测文件的编码"""
        data = cls._read_raw(file_path) if raw_data is None else raw_data
        if not data:
            return "UTF-8", "utf-8"
        return cls._detect_from_bytes(data)

    @classmethod
    def detect_bytes(cls, raw_data: bytes) -> tuple[str, str]:
        """检测字节序列的编码"""
        return cls._detect_from_bytes(raw_data)

    @classmethod
    def diagnose_detect(
        cls,
        file_path: str | Path,
        raw_data: bytes | None = None,
    ) -> tuple[list[tuple[str, str, str]], str, bool]:
        """诊断检测：返回各编码解码尝试详情"""
        data = cls._read_raw(file_path) if raw_data is None else raw_data
        return diagnose_bytes(data)

    @staticmethod
    def charset_detect(raw_data: bytes) -> dict:
        """使用 charset-normalizer 做交叉参考检测"""
        try:
            import charset_normalizer
        except ImportError:
            return {"encoding": "", "confidence": 0}

        result = charset_normalizer.detect(raw_data)
        return {
            "encoding": result.get("encoding", ""),
            "confidence": result.get("confidence", 0),
        }

    @classmethod
    def file_to_tokens(
        cls,
        file_path: str | Path,
        raw_data: bytes | None = None,
    ):
        """将文件解码为 CharacterToken 列表"""
        data = cls._read_raw(file_path) if raw_data is None else raw_data
        if not data:
            return []

        display_name, std_name = cls.detect_file(file_path, raw_data=data)
        return tokens_from_bytes(data, display_name, std_name, file_path)
