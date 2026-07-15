"""测试编码注册表 —— 确保 UTF-16 已从用户可选项中移除，但内部 codec 仍可用"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from encoding import (
    ALL_ENCODINGS,
    CONVERTER_ENCODING_MAP,
    ENCODING_BY_NAME,
    ENCODING_NAMES,
    VIEWER_ENCODING_MAP,
)
from converter.converter import Converter


class TestEncodingRegistry(unittest.TestCase):
    """验证 UTF-16 已从用户可选项中移除，但内部 codec 仍可用"""

    def test_no_utf16_in_all_encodings(self):
        names = [e.display_name for e in ALL_ENCODINGS]
        self.assertNotIn("UTF-16", names)
        self.assertIn("UTF-16 LE", names)
        self.assertIn("UTF-16 BE", names)

    def test_no_utf16_in_encoding_names(self):
        self.assertNotIn("UTF-16", ENCODING_NAMES)
        self.assertIn("UTF-16 LE", ENCODING_NAMES)
        self.assertIn("UTF-16 BE", ENCODING_NAMES)

    def test_no_utf16_in_encoding_by_name(self):
        self.assertNotIn("UTF-16", ENCODING_BY_NAME)
        self.assertIn("UTF-16 LE", ENCODING_BY_NAME)
        self.assertIn("UTF-16 BE", ENCODING_BY_NAME)

    def test_no_utf16_in_viewer_map(self):
        self.assertNotIn("UTF-16", VIEWER_ENCODING_MAP)
        self.assertIn("UTF-16 LE", VIEWER_ENCODING_MAP)
        self.assertIn("UTF-16 BE", VIEWER_ENCODING_MAP)

    def test_no_utf16_in_converter_map(self):
        self.assertNotIn("UTF-16", CONVERTER_ENCODING_MAP)
        self.assertIn("UTF-16 LE", CONVERTER_ENCODING_MAP)
        self.assertIn("UTF-16 BE", CONVERTER_ENCODING_MAP)

    def test_converter_maps_utf16le_to_codec(self):
        self.assertEqual(CONVERTER_ENCODING_MAP["UTF-16 LE"], "utf-16-le")

    def test_converter_maps_utf16be_to_codec(self):
        self.assertEqual(CONVERTER_ENCODING_MAP["UTF-16 BE"], "utf-16-be")

    def test_internal_utf16_codec_is_still_available(self):
        text = "Hello"
        encoded = text.encode("utf-16")
        self.assertIn(encoded[:2], (b"\xff\xfe", b"\xfe\xff"))
        self.assertEqual(encoded[2:], text.encode("utf-16-le"))

    def test_internal_utf16le_codec_works(self):
        text = "Hello"
        encoded = text.encode("utf-16-le")
        decoded = encoded.decode("utf-16-le")
        self.assertEqual(decoded, text)

    def test_internal_utf16be_codec_works(self):
        text = "Hello"
        encoded = text.encode("utf-16-be")
        decoded = encoded.decode("utf-16-be")
        self.assertEqual(decoded, text)

    def test_converter_still_supports_utf16le_target(self):
        tgt_std = Converter.SUPPORTED_ENCODINGS.get("UTF-16 LE")
        self.assertEqual(tgt_std, "utf-16-le")

    def test_converter_still_supports_utf16be_target(self):
        tgt_std = Converter.SUPPORTED_ENCODINGS.get("UTF-16 BE")
        self.assertEqual(tgt_std, "utf-16-be")

    def test_converter_fallback_for_removed_utf16(self):
        tgt_std = Converter.SUPPORTED_ENCODINGS.get("UTF-16", "utf-8")
        self.assertEqual(tgt_std, "utf-8")

    def test_converter_encoding_count(self):
        self.assertEqual(len(CONVERTER_ENCODING_MAP), 9)
        self.assertEqual(len(ALL_ENCODINGS), 9)


if __name__ == "__main__":
    unittest.main()
