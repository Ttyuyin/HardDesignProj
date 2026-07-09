"""
EncodingViewer tests — display char, analyze character/token/tokens, statistics.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from encoding_viewer import EncodingViewer
from character_token import CharacterToken


class TestGetDisplayChar(unittest.TestCase):
    def test_normal_char(self):
        self.assertEqual(EncodingViewer.get_display_char("A"), "A")

    def test_cjk_char(self):
        self.assertEqual(EncodingViewer.get_display_char("中"), "中")

    def test_null(self):
        self.assertEqual(EncodingViewer.get_display_char("\x00"), "[NUL]")

    def test_space(self):
        self.assertEqual(EncodingViewer.get_display_char(" "), "[SP]")

    def test_nbsp(self):
        self.assertEqual(EncodingViewer.get_display_char("\xA0"), "[NBSP]")

    def test_tab(self):
        self.assertEqual(EncodingViewer.get_display_char("\t"), "[TAB]")

    def test_del(self):
        self.assertEqual(EncodingViewer.get_display_char("\x7F"), "[DEL]")


class TestAnalyzeCharacter(unittest.TestCase):
    def test_ascii_char_result_keys(self):
        result = EncodingViewer.analyze_character("A")
        self.assertIn("Char", result)
        self.assertIn("Unicode", result)
        self.assertIn("Raw Bytes", result)
        self.assertIn("ASCII", result)
        self.assertIn("GBK", result)

    def test_ascii_char_values(self):
        result = EncodingViewer.analyze_character("A")
        self.assertEqual(result["Char"], "A")
        self.assertEqual(result["Unicode"], "U+0041")
        self.assertEqual(result["ASCII"], "41")
        self.assertEqual(result["GBK"], "41")

    def test_cjk_char_gbk_not_na(self):
        result = EncodingViewer.analyze_character("中")
        self.assertNotEqual(result["GBK"], "N/A")

    def test_cjk_char_ascii_is_na(self):
        result = EncodingViewer.analyze_character("中")
        self.assertEqual(result["ASCII"], "N/A")

    def test_unicode_codepoint(self):
        result = EncodingViewer.analyze_character("€")
        self.assertEqual(result["Unicode"], "U+20AC")

    def test_raw_bytes_from_source(self):
        result = EncodingViewer.analyze_character("A", source_bytes=b"\x41")
        self.assertEqual(result["Raw Bytes"], "41")

    def test_raw_bytes_from_source_encoding(self):
        result = EncodingViewer.analyze_character("中", source_encoding="GBK",
                                                   source_bytes=b"\xd6\xd0")
        self.assertEqual(result["Raw Bytes"], "D6 D0")


class TestAnalyzeToken(unittest.TestCase):
    def test_token_analyzed(self):
        token = CharacterToken(char="中", source_encoding="GBK",
                               source_bytes=b"\xd6\xd0")
        result = EncodingViewer.analyze_token(token)
        self.assertEqual(result["Char"], "中")
        self.assertEqual(result["Source Encoding"], "GBK")
        self.assertEqual(result["Raw Bytes"], "D6 D0")

    def test_fallback_encoding_used(self):
        token = CharacterToken(char="中", source_encoding="")
        result = EncodingViewer.analyze_token(token, fallback_encoding="GBK")
        self.assertEqual(result["Raw Bytes"], "D6 D0")


class TestAnalyzeTokens(unittest.TestCase):
    def test_multiple_tokens(self):
        tokens = [
            CharacterToken(char="H", source_encoding="UTF-8", source_bytes=b"H"),
            CharacterToken(char="i", source_encoding="UTF-8", source_bytes=b"i"),
        ]
        results = EncodingViewer.analyze_tokens(tokens)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["Char"], "H")
        self.assertEqual(results[1]["Char"], "i")

    def test_empty_tokens(self):
        results = EncodingViewer.analyze_tokens([])
        self.assertEqual(results, [])


class TestGetStatistics(unittest.TestCase):
    def test_all_supported(self):
        results = [
            EncodingViewer.analyze_character("A"),
            EncodingViewer.analyze_character("B"),
        ]
        stats = EncodingViewer.get_statistics(results)
        self.assertEqual(stats["total_chars"], 2)
        ascii_stats = stats["encoding_stats"]["ASCII"]
        self.assertEqual(ascii_stats["supported"], 2)
        self.assertEqual(ascii_stats["rate"], 100.0)

    def test_partial_support(self):
        results = [
            EncodingViewer.analyze_character("A"),
            EncodingViewer.analyze_character("中"),
        ]
        stats = EncodingViewer.get_statistics(results)
        ascii_stats = stats["encoding_stats"]["ASCII"]
        self.assertEqual(ascii_stats["supported"], 1)
        self.assertEqual(ascii_stats["unsupported"], 1)
        self.assertAlmostEqual(ascii_stats["rate"], 50.0)

    def test_empty_results_has_zero_rate(self):
        stats = EncodingViewer.get_statistics([])
        self.assertEqual(stats["total_chars"], 0)
        for enc_stats in stats["encoding_stats"].values():
            self.assertEqual(enc_stats["rate"], 0.0)

    def test_encoded_bytes_format(self):
        result = EncodingViewer.analyze_character("A")
        self.assertEqual(result["ASCII"], "41")


if __name__ == '__main__':
    unittest.main(verbosity=2)
