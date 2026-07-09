"""
Verifier tests — ConversionVerdict + ConversionVerifier.verify_roundtrip.
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from verifier import ConversionVerdict, ConversionVerifier
from character_token import CharacterToken


class TestConversionVerdict(unittest.TestCase):
    def test_all_match_true(self):
        v = ConversionVerdict(total_chars=5, match_count=5)
        self.assertTrue(v.all_match)

    def test_all_match_false_on_mismatch(self):
        v = ConversionVerdict(total_chars=5, match_count=4, mismatch_count=1)
        self.assertFalse(v.all_match)

    def test_all_match_false_on_zero_total(self):
        v = ConversionVerdict(total_chars=0, match_count=0)
        self.assertFalse(v.all_match)

    def test_error_field(self):
        v = ConversionVerdict(error="Something broke")
        self.assertEqual(v.error, "Something broke")
        self.assertFalse(v.all_match)

    def test_default_values(self):
        v = ConversionVerdict()
        self.assertEqual(v.total_chars, 0)
        self.assertEqual(v.mismatches, [])
        self.assertIsNone(v.error)


class TestVerifyRoundtrip(unittest.TestCase):
    def test_perfect_roundtrip(self):
        tokens = [CharacterToken(char=c, source_encoding="UTF-8", source_bytes=c.encode())
                  for c in "Hello"]
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="wb") as f:
            f.write("Hello".encode("utf-8"))
            tmp = f.name
        try:
            verdict = ConversionVerifier.verify_roundtrip(tokens, tmp, "UTF-8")
            self.assertTrue(verdict.is_valid_target_encoding)
            self.assertTrue(verdict.all_match)
            self.assertIsNone(verdict.error)
        finally:
            os.unlink(tmp)

    def test_file_not_found(self):
        tokens = [CharacterToken(char="A", source_encoding="UTF-8", source_bytes=b"A")]
        verdict = ConversionVerifier.verify_roundtrip(tokens, "/nonexistent/file.txt", "UTF-8")
        self.assertIsNotNone(verdict.error)
        self.assertIn("not found", verdict.error)

    def test_invalid_target_encoding(self):
        tokens = [CharacterToken(char="A", source_encoding="UTF-8", source_bytes=b"A")]
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="wb") as f:
            f.write(b"\xff\xfe\xff\xfe")
            tmp = f.name
        try:
            verdict = ConversionVerifier.verify_roundtrip(tokens, tmp, "UTF-8")
            self.assertFalse(verdict.is_valid_target_encoding)
        finally:
            os.unlink(tmp)

    def test_mismatch_detected(self):
        tokens = [CharacterToken(char="A", source_encoding="UTF-8", source_bytes=b"A")]
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="wb") as f:
            f.write(b"B")
            tmp = f.name
        try:
            verdict = ConversionVerifier.verify_roundtrip(tokens, tmp, "UTF-8")
            self.assertTrue(verdict.is_valid_target_encoding)
            self.assertEqual(verdict.mismatch_count, 1)
            self.assertEqual(verdict.match_count, 0)
            self.assertFalse(verdict.all_match)
        finally:
            os.unlink(tmp)

    def test_mismatch_logs_details(self):
        tokens = [CharacterToken(char="A", source_encoding="UTF-8", source_bytes=b"A")]
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="wb") as f:
            f.write(b"B")
            tmp = f.name
        try:
            verdict = ConversionVerifier.verify_roundtrip(tokens, tmp, "UTF-8")
            self.assertGreater(len(verdict.mismatches), 0)
            self.assertIn("original", verdict.mismatches[0])
            self.assertIn("recovered", verdict.mismatches[0])
        finally:
            os.unlink(tmp)

    def test_length_mismatch_logged(self):
        tokens = [CharacterToken(char=c, source_encoding="UTF-8", source_bytes=c.encode())
                  for c in "Hello"]
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="wb") as f:
            f.write("Hi".encode("utf-8"))
            tmp = f.name
        try:
            verdict = ConversionVerifier.verify_roundtrip(tokens, tmp, "UTF-8")
            has_len_note = any("Length mismatch" in str(m) for m in verdict.mismatches)
            self.assertTrue(has_len_note)
        finally:
            os.unlink(tmp)


if __name__ == '__main__':
    unittest.main(verbosity=2)
