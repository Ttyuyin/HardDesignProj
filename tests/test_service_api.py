"""
Service API tests — verify result types and field contracts.
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.result import DetectionResult, CompatibilitySummary, ConversionResult


class TestDetectionResult(unittest.TestCase):
    def test_fields_exist(self):
        r = DetectionResult(encoding="GBK", std_name="gbk")
        self.assertEqual(r.encoding, "GBK")
        self.assertEqual(r.std_name, "gbk")
        self.assertFalse(r.is_pure_ascii)
        self.assertEqual(r.trials, [])

    def test_is_pure_ascii_default(self):
        r = DetectionResult(encoding="ASCII", std_name="utf-8")
        self.assertFalse(r.is_pure_ascii)

    def test_can_set_trials(self):
        r = DetectionResult(encoding="UTF-8", std_name="utf-8",
                            trials=[("UTF-8 BOM", "efbbbf", "BOM matched")])
        self.assertEqual(len(r.trials), 1)


class TestCompatibilitySummary(unittest.TestCase):
    def test_fields_exist(self):
        s = CompatibilitySummary(rate=85.0, compatible=17, total=20,
                                 problem_count=3, problems=[{"char": "?"}])
        self.assertEqual(s.rate, 85.0)
        self.assertEqual(s.compatible, 17)
        self.assertEqual(s.total, 20)
        self.assertEqual(s.problem_count, 3)
        self.assertEqual(len(s.problems), 1)

    def test_defaults(self):
        s = CompatibilitySummary()
        self.assertEqual(s.rate, 100.0)
        self.assertEqual(s.problem_count, 0)


class TestConversionResult(unittest.TestCase):
    def test_fields_exist(self):
        r = ConversionResult(
            path=Path("/tmp/out.txt"),
            tokens=[],
            total_chars=10,
            verified=True,
            reversible=True,
            all_match=True,
            match_count=10,
            mismatch_count=0,
            mismatch_log=["Verifier: 10/10 match"],
        )
        self.assertEqual(r.path, Path("/tmp/out.txt"))
        self.assertEqual(r.total_chars, 10)
        self.assertTrue(r.verified)
        self.assertTrue(r.reversible)
        self.assertTrue(r.all_match)
        self.assertEqual(r.match_count, 10)
        self.assertEqual(len(r.mismatch_log), 1)


class TestServiceFunctions(unittest.TestCase):
    """Integration-lite: verify service functions return correct types."""

    def setUp(self):
        self.chars_dir = Path(os.path.join(os.path.dirname(__file__), '..', 'chars'))
        self.sample_file = self.chars_dir / "numbers.txt"

    def test_detect_bytes_returns_detection_result(self):
        from services.detector_service import detect_bytes
        r = detect_bytes(b"Hello World")
        self.assertIsInstance(r.encoding, str)
        self.assertIsInstance(r.std_name, str)

    def test_detect_bytes_ascii(self):
        from services.detector_service import detect_bytes
        r = detect_bytes(b"Hello World 123")
        self.assertEqual(r.encoding, "ASCII")

    def test_file_to_tokens_returns_list(self):
        from services.detector_service import file_to_tokens
        if not self.sample_file.is_file():
            self.skipTest("numbers.txt not found")
        tokens = file_to_tokens(self.sample_file)
        self.assertIsInstance(tokens, list)

    def test_charset_detect_returns_dict(self):
        from services.detector_service import charset_detect
        r = charset_detect(b"Hello")
        self.assertIn("encoding", r)
        self.assertIn("confidence", r)

    def test_compatibility_scan_returns_compatibility_summary(self):
        from services.converter_service import compatibility_scan
        from character_token import CharacterToken
        t = [CharacterToken(char='H', source_encoding="UTF-8", source_bytes=b"H")]
        r = compatibility_scan(t, "GBK")
        self.assertIsInstance(r.rate, float)
        self.assertIsInstance(r.compatible, int)
        self.assertIsInstance(r.problem_count, int)

    def test_convert_file_returns_conversion_result(self):
        from services.converter_service import convert_file
        from character_token import CharacterToken
        import tempfile
        t = [CharacterToken(char='H', source_encoding="UTF-8", source_bytes=b"H")]
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "test.txt"
            src.write_text("H", encoding="utf-8")
            r = convert_file(src, t, "UTF-8", "GBK", tmp)
        self.assertIsInstance(r.path, Path)
        self.assertIsInstance(r.total_chars, int)
        self.assertIsInstance(r.verified, bool)


if __name__ == '__main__':
    unittest.main(verbosity=2)
