"""
检测功能测试 —— 验证重构后检测不降级
BOM 确定性、UTF-16 无 BOM、CJK 编码竞争等核心场景
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from detector.pipeline import detect_with_full_decision


class TestBOMDetection(unittest.TestCase):
    """BOM 检测是确定性事实，必须 100% 准确"""

    def test_utf16le_bom(self):
        result = detect_with_full_decision(b"\xff\xfeH\x00e\x00")
        self.assertEqual(result["encoding"], "UTF-16 LE")
        self.assertEqual(result["confidence"], 1.0)

    def test_utf16be_bom(self):
        result = detect_with_full_decision(b"\xfe\xff\x00H\x00e")
        self.assertEqual(result["encoding"], "UTF-16 BE")
        self.assertEqual(result["confidence"], 1.0)

    def test_utf8_bom(self):
        result = detect_with_full_decision(b"\xef\xbb\xbfHello")
        self.assertEqual(result["encoding"], "UTF-8")
        self.assertEqual(result["std_name"], "utf-8-sig")
        self.assertEqual(result["confidence"], 1.0)


class TestASCIIShortCircuit(unittest.TestCase):
    """纯 ASCII 且长度足够时短路返回"""

    def test_ascii_long_enough(self):
        result = detect_with_full_decision(b"Hello World! This is ASCII text")
        self.assertEqual(result["encoding"], "ASCII")

    def test_ascii_too_short_goes_through_agents(self):
        """短文本不走 ASCII 短路，由 Agent 竞争决定"""
        result = detect_with_full_decision(b"Hi")
        self.assertEqual(result["encoding"], "UTF-8")

    def test_exactly_ten_chars(self):
        result = detect_with_full_decision(b"1234567890")
        self.assertEqual(result["encoding"], "ASCII")


class TestUTF16NoBOM(unittest.TestCase):
    """UTF-16 无 BOM 文本通过 Agent 评分 + anchor hint"""

    def test_utf16le_no_bom(self):
        result = detect_with_full_decision(b"H\x00e\x00l\x00l\x00o\x00")
        self.assertEqual(result["encoding"], "UTF-16 LE")

    def test_utf16be_no_bom(self):
        result = detect_with_full_decision(b"\x00H\x00e\x00l\x00l\x00o")
        self.assertEqual(result["encoding"], "UTF-16 BE")


class TestCJKDetection(unittest.TestCase):
    """CJK 编码竞争检测"""

    def test_gbk_chinese(self):
        data = "你好世界".encode("gbk")
        result = detect_with_full_decision(data)
        self.assertEqual(result["encoding"], "GBK")
        self.assertGreater(result["confidence"], 0.5)

    def test_big5_chinese(self):
        data = "你好世界".encode("big5")
        result = detect_with_full_decision(data)
        self.assertEqual(result["encoding"], "Big5")
        self.assertGreater(result["confidence"], 0.5)

    def test_shift_jis(self):
        data = "こんにちは".encode("cp932")
        result = detect_with_full_decision(data)
        self.assertEqual(result["encoding"], "Shift-JIS")
        self.assertGreater(result["confidence"], 0.5)

    def test_utf8_chinese(self):
        data = "你好世界".encode("utf-8")
        result = detect_with_full_decision(data)
        self.assertEqual(result["encoding"], "UTF-8")
        self.assertGreater(result["confidence"], 0.5)


class TestResultStructure(unittest.TestCase):
    """验证返回结果结构一致"""

    def test_result_has_all_keys(self):
        result = detect_with_full_decision(b"Hello World")
        self.assertIn("encoding", result)
        self.assertIn("std_name", result)
        self.assertIn("confidence", result)
        self.assertIn("top_candidates", result)

    def test_top_candidates_are_sorted(self):
        result = detect_with_full_decision("你好世界".encode("gbk"))
        probs = [p for _, p in result["top_candidates"]]
        for i in range(len(probs) - 1):
            self.assertGreaterEqual(probs[i], probs[i + 1])


if __name__ == "__main__":
    unittest.main()
