"""
Converter tests — encoding_converter logic: Converter class + convert_file.
"""

import os
import sys
import unittest
from pathlib import Path
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from encoding_converter import Converter, convert_file
from character_token import CharacterToken


class TestConverterSafeName(unittest.TestCase):
    def test_spaces_replaced(self):
        self.assertEqual(Converter._safe_name("UTF-16 LE"), "utf16_le")

    def test_hyphens_removed(self):
        self.assertEqual(Converter._safe_name("UTF-16"), "utf16")

    def test_lowercased(self):
        self.assertEqual(Converter._safe_name("GBK"), "gbk")

    def test_mixed_special_chars(self):
        self.assertEqual(Converter._safe_name("Shift-JIS"), "shiftjis")


class TestConverterEncode(unittest.TestCase):
    def test_ascii_char(self):
        result = Converter._encode("A", "ascii", "replace")
        self.assertEqual(result, b"A")

    def test_gbk_char(self):
        result = Converter._encode("中", "gbk", "replace")
        self.assertEqual(result, b"\xd6\xd0")

    def test_big5_char(self):
        result = Converter._encode("中", "big5", "replace")
        self.assertEqual(result, b"\xa4\xa4")

    def test_utf16_le(self):
        result = Converter._encode("A", "utf-16-le", "replace")
        self.assertEqual(result, b"A\x00")

    def test_utf16_be(self):
        result = Converter._encode("A", "utf-16-be", "replace")
        self.assertEqual(result, b"\x00A")

    def test_unencodable_replaced(self):
        result = Converter._encode("\u20AC", "ascii", "replace")
        self.assertEqual(result, b"?")

    def test_strict_raises(self):
        with self.assertRaises(ValueError):
            Converter._encode("\u20AC", "ascii", "strict")


class TestConverterConvertTokens(unittest.TestCase):
    def test_single_token(self):
        tokens = [CharacterToken(char="A", source_encoding="UTF-8", source_bytes=b"A")]
        output, processed = Converter.convert_tokens(tokens, "GBK")
        self.assertEqual(output, b"A")
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0].target_encoding, "GBK")

    def test_multi_token(self):
        tokens = [
            CharacterToken(char="H", source_encoding="UTF-8", source_bytes=b"H"),
            CharacterToken(char="i", source_encoding="UTF-8", source_bytes=b"i"),
        ]
        output, processed = Converter.convert_tokens(tokens, "ASCII")
        self.assertEqual(output, b"Hi")

    def test_cjk_token(self):
        tokens = [CharacterToken(char="你", source_encoding="UTF-8", source_bytes=b"\xe4\xbd\xa0")]
        output, processed = Converter.convert_tokens(tokens, "GBK")
        self.assertEqual(output, b"\xc4\xe3")

    def test_unencodable_in_strict_raises(self):
        tokens = [CharacterToken(char="\u20AC", source_encoding="UTF-8", source_bytes=b"\xe2\x82\xac")]
        with self.assertRaises(ValueError):
            Converter.convert_tokens(tokens, "ASCII", error_strategy="strict")

    def test_target_encoding_set_on_tokens(self):
        tokens = [CharacterToken(char="A", source_encoding="UTF-8", source_bytes=b"A")]
        _, processed = Converter.convert_tokens(tokens, "GBK")
        self.assertEqual(processed[0].target_encoding, "GBK")


class TestConverterOutputPath(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_default_output_name(self):
        src = Path(self.tmpdir) / "test.txt"
        src.write_text("hello", encoding="utf-8")
        out = Converter._output_path(src, "UTF-8", "GBK")
        self.assertIn("test", out.name)
        self.assertIn("utf8_to_gbk", out.name)

    def test_custom_output_dir(self):
        custom = Path(self.tmpdir) / "custom"
        src = Path(self.tmpdir) / "test.txt"
        src.write_text("hello", encoding="utf-8")
        out = Converter._output_path(src, "GBK", "Big5", output_dir=custom)
        self.assertTrue(str(out).startswith(str(custom)))

    def test_no_suffix_uses_txt(self):
        src = Path(self.tmpdir) / "test"
        src.write_text("hello", encoding="utf-8")
        out = Converter._output_path(src, "UTF-8", "GBK")
        self.assertTrue(out.name.endswith(".txt"))


class TestConvertFile(unittest.TestCase):
    def test_basic_conversion(self):
        tokens = [CharacterToken(char="H", source_encoding="UTF-8", source_bytes=b"H")]
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "test.txt"
            src.write_text("H", encoding="utf-8")
            result = convert_file(src, tokens, "UTF-8", "GBK", tmp)
            self.assertIsInstance(result["path"], Path)
            self.assertTrue(result["path"].exists())
            self.assertEqual(result["total_chars"], 1)

    def test_output_content(self):
        tokens = [
            CharacterToken(char="H", source_encoding="UTF-8", source_bytes=b"H"),
            CharacterToken(char="i", source_encoding="UTF-8", source_bytes=b"i"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "test.txt"
            src.write_text("Hi", encoding="utf-8")
            result = convert_file(src, tokens, "UTF-8", "ASCII", tmp)
            content = result["path"].read_bytes()
            self.assertEqual(content, b"Hi")

    def test_verified_flag(self):
        tokens = [CharacterToken(char="H", source_encoding="UTF-8", source_bytes=b"H")]
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "test.txt"
            src.write_text("H", encoding="utf-8")
            result = convert_file(src, tokens, "UTF-8", "GBK", tmp)
            self.assertIn("verified", result)
            self.assertIn("reversible", result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
