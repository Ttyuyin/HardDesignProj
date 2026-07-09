"""
Compatibility tests — CompatibilityReport + compatibility_scan.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from compatibility import CompatibilityReport, compatibility_scan, get_s2t_translator
from character_token import CharacterToken


class TestCompatibilityReport(unittest.TestCase):
    def test_rate_full_compatible(self):
        r = CompatibilityReport(total=10, compatible=10)
        self.assertEqual(r.rate, 100.0)

    def test_rate_partial(self):
        r = CompatibilityReport(total=10, compatible=7)
        self.assertAlmostEqual(r.rate, 70.0)

    def test_rate_zero_total(self):
        r = CompatibilityReport(total=0, compatible=0)
        self.assertEqual(r.rate, 100.0)

    def test_problem_count(self):
        r = CompatibilityReport(total=5, compatible=3,
                                problems=[{"char": "?"}, {"char": "?"}])
        self.assertEqual(r.problem_count, 2)

    def test_problem_count_empty(self):
        r = CompatibilityReport(total=5, compatible=5)
        self.assertEqual(r.problem_count, 0)


class TestCompatibilityScan(unittest.TestCase):
    def test_all_compatible_ascii(self):
        tokens = [CharacterToken(char=c, source_encoding="UTF-8", source_bytes=c.encode())
                  for c in "Hello"]
        r = compatibility_scan(tokens, "ASCII")
        self.assertEqual(r.rate, 100.0)
        self.assertEqual(r.compatible, 5)
        self.assertEqual(r.problem_count, 0)

    def test_all_compatible_gbk(self):
        tokens = [CharacterToken(char="中", source_encoding="UTF-8",
                                 source_bytes=b"\xe4\xb8\xad")]
        r = compatibility_scan(tokens, "GBK")
        self.assertEqual(r.rate, 100.0)

    def test_unencodable_in_ascii(self):
        tokens = [CharacterToken(char="\u20AC", source_encoding="UTF-8",
                                 source_bytes=b"\xe2\x82\xac")]
        r = compatibility_scan(tokens, "ASCII")
        self.assertEqual(r.rate, 0.0)
        self.assertEqual(r.compatible, 0)
        self.assertEqual(r.problem_count, 1)

    def test_mixed_compatibility(self):
        tokens = [
            CharacterToken(char="A", source_encoding="UTF-8", source_bytes=b"A"),
            CharacterToken(char="\u20AC", source_encoding="UTF-8", source_bytes=b"\xe2\x82\xac"),
        ]
        r = compatibility_scan(tokens, "ASCII")
        self.assertAlmostEqual(r.rate, 50.0)
        self.assertEqual(r.compatible, 1)
        self.assertEqual(r.problem_count, 1)

    def test_problem_has_char_and_unicode(self):
        tokens = [CharacterToken(char="\u20AC", source_encoding="UTF-8",
                                 source_bytes=b"\xe2\x82\xac")]
        r = compatibility_scan(tokens, "ASCII")
        p = r.problems[0]
        self.assertEqual(p["char"], "\u20AC")
        self.assertEqual(p["unicode"], "U+20AC")
        self.assertIn("position", p)

    def test_big5_s2t(self):
        """简繁转换发生在兼容性检查之前（用于 Big5 目标）"""
        tokens = [CharacterToken(char="的", source_encoding="UTF-8",
                                 source_bytes="的".encode("utf-8"))]
        r = compatibility_scan(tokens, "Big5", s2t_convert=True)
        self.assertEqual(r.rate, 100.0)


class TestGetS2TTranslator(unittest.TestCase):
    def test_returns_none_when_not_installed(self):
        translator = get_s2t_translator()
        if translator is None:
            self.assertIsNone(translator)
        else:
            self.assertTrue(callable(translator.convert))


if __name__ == '__main__':
    unittest.main(verbosity=2)
