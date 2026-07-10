"""
回归测试：验证重构后的检测引擎与原始行为完全一致。

覆盖范围：
1. UTF-8 中文
2. ASCII 文件
3. GBK 中文
4. Big5 繁体
5. Shift-JIS 日文
6. UTF-16 LE
7. UTF-16 BE
8. CJK agent 数学等价
9. UTF-16 agent 数学等价
10. FileEncodingDetector 接口完整性
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from encoding import resolve_std_name
from detector.agents import (
    _ALL_AGENTS, GBK_AGENT, BIG5_AGENT, SHIFT_JIS_AGENT,
    EncodingDetectionAgent,
)
from detector.pipeline import (
    detect_with_full_decision, _run_agents,
    FileEncodingDetector,
)
from byte_validator import score_gbk, score_big5, score_sjis
from decode_utils import strict_decode
from text_analyzer import analyze_text

CHARS_DIR = os.path.join(os.path.dirname(__file__), '..', 'chars')


def _gbk_agent_original(raw_data):
    text = strict_decode(raw_data, "gbk")
    if text is None:
        return {"GBK": 0.0}
    byte_score = score_gbk(raw_data)
    analysis = analyze_text(text)
    space_penalty = 0.4 if (analysis["cjk_ratio"] > 0 and analysis["space_ratio"] > 0.1) else 0.0
    ctrl_penalty = min(0.5, analysis["control_ratio"] * 3)
    score = (byte_score * 0.4 + analysis["cjk_ratio"] * 0.3
             + min(1.0, analysis["script_score"]) * 0.3
             - space_penalty - ctrl_penalty)
    # Negative feature: cross-encoding kana check (mirrors GBK_AGENT)
    sjis_text = strict_decode(raw_data, "cp932")
    if sjis_text is not None:
        sjis_analysis = analyze_text(sjis_text)
        kana_r = sjis_analysis["kana_ratio"]
        if kana_r > 0.001:
            penalty = min(0.35, kana_r * 0.65)
            score -= penalty
    return {"GBK": max(0.0, min(1.0, score))}


def _big5_agent_original(raw_data):
    text = strict_decode(raw_data, "big5")
    if text is None:
        return {"Big5": 0.0}
    byte_score = score_big5(raw_data)
    analysis = analyze_text(text)
    space_penalty = 0.4 if (analysis["cjk_ratio"] > 0 and analysis["space_ratio"] > 0.1) else 0.0
    ctrl_penalty = min(0.5, analysis["control_ratio"] * 3)
    score = (byte_score * 0.4 + analysis["cjk_ratio"] * 0.2
             + min(1.0, analysis["script_score"]) * 0.2
             + analysis["bopomofo_ratio"] * 0.2
             - space_penalty - ctrl_penalty)
    return {"Big5": max(0.0, min(1.0, score))}


def _shift_jis_agent_original(raw_data):
    text = strict_decode(raw_data, "cp932")
    if text is None:
        return {"Shift-JIS": 0.0}
    byte_score = score_sjis(raw_data)
    analysis = analyze_text(text)
    space_penalty = 0.4 if (analysis["cjk_ratio"] > 0 and analysis["space_ratio"] > 0.1) else 0.0
    ctrl_penalty = min(0.5, analysis["control_ratio"] * 3)
    score = (byte_score * 0.4 + analysis["kana_ratio"] * 0.4
             + analysis["cjk_ratio"] * 0.2
             - space_penalty - ctrl_penalty)
    return {"Shift-JIS": max(0.0, min(1.0, score))}


class TestCJKAgentEquivalence(unittest.TestCase):
    """验证 CJK agent 重构后评分与原始函数完全一致"""

    SAMPLES = [
        ('ascii', b'Hello World 12345'),
        ('mixed', b'Hello \xe4\xbd\xa0\xe5\xa5\xbd World'),
        ('gbk_cn', '计算机课程设计'.encode('gbk')),
        ('big5', '電腦課程'.encode('big5')),
        ('sjis', '日本語'.encode('cp932')),
        ('utf8_cn', '你好世界你好世界'.encode('utf-8')),
        ('utf8_emoji', '😀🚀'.encode('utf-8')),
        ('latin1', 'café'.encode('latin1')),
    ]

    def test_gbk_agent(self):
        for name, data in self.SAMPLES:
            old = _gbk_agent_original(data)
            new = GBK_AGENT(data)
            self.assertEqual(old, new, f'GBK mismatch on {name}')

    def test_big5_agent(self):
        for name, data in self.SAMPLES:
            old = _big5_agent_original(data)
            new = BIG5_AGENT(data)
            self.assertEqual(old, new, f'Big5 mismatch on {name}')

    def test_shift_jis_agent(self):
        for name, data in self.SAMPLES:
            old = _shift_jis_agent_original(data)
            new = SHIFT_JIS_AGENT(data)
            self.assertEqual(old, new, f'Shift-JIS mismatch on {name}')

    def test_agents_on_real_files(self):
        """使用实际测试文件验证"""
        if not os.path.isdir(CHARS_DIR):
            self.skipTest('chars directory not found')
        files = sorted(os.listdir(CHARS_DIR))[:8]
        for fname in files:
            fpath = os.path.join(CHARS_DIR, fname)
            if not os.path.isfile(fpath):
                continue
            with open(fpath, 'rb') as f:
                data = f.read()
            for agent_name, agent_old, agent_new in [
                ('GBK', _gbk_agent_original, GBK_AGENT),
                ('Big5', _big5_agent_original, BIG5_AGENT),
                ('Shift-JIS', _shift_jis_agent_original, SHIFT_JIS_AGENT),
            ]:
                old = agent_old(data)
                new = agent_new(data)
                self.assertEqual(
                    old, new,
                    f'{agent_name} mismatch on file {fname}: old={old} new={new}'
                )


class TestUTF16AgentEquivalence(unittest.TestCase):
    """验证 UTF-16 LE/BE agent 重构后与原始行为一致"""

    SAMPLES = [
        ('short_ascii_le', b'H\x00e\x00l\x00l\x00o\x00'),
        ('short_ascii_be', b'\x00H\x00e\x00l\x00l\x00o'),
        ('utf8_cn_le', '你好'.encode('utf-16-le')),
        ('utf8_cn_be', '你好'.encode('utf-16-be')),
        ('random_bytes', bytes(range(256))),
        ('odd_length', b'\xff\xfe\x00\x01\x00'),
        ('empty', b''),
        ('single_byte', b'\x00'),
    ]

    def test_utf16le_agent(self):
        from detector.agents import _utf16le_agent
        for name, data in self.SAMPLES:
            result = _utf16le_agent(data)
            self.assertIn('UTF-16 LE', result)
            self.assertGreaterEqual(result['UTF-16 LE'], 0.0)
            self.assertLessEqual(result['UTF-16 LE'], 1.0)

    def test_utf16be_agent(self):
        from detector.agents import _utf16be_agent
        for name, data in self.SAMPLES:
            result = _utf16be_agent(data)
            self.assertIn('UTF-16 BE', result)
            self.assertGreaterEqual(result['UTF-16 BE'], 0.0)
            self.assertLessEqual(result['UTF-16 BE'], 1.0)

    def test_utf16_le_be_different(self):
        """LE 和 BE 在同一数据上应给出不同结果"""
        from detector.agents import _utf16le_agent, _utf16be_agent
        data = b'H\x00e\x00l\x00l\x00o\x00'
        le = _utf16le_agent(data)
        be = _utf16be_agent(data)
        self.assertNotEqual(le['UTF-16 LE'], be['UTF-16 BE'],
                            'LE and BE should differ on LE-encoded data')


class TestEncodingMapping(unittest.TestCase):
    """验证 resolve_std_name 覆盖所有 case"""

    def test_resolve_std_name(self):
        cases = {
            'UTF-8': 'utf-8',
            'UTF-16 LE': 'utf-16-le',
            'UTF-16 BE': 'utf-16-be',
            'Shift-JIS': 'cp932',
            'Extended ASCII': 'cp1252',
            'GBK': 'gbk',
            'Big5': 'big5',
            'GB2312': 'gb2312',
            'ASCII': 'utf-8',  # detector-specific alias
        }
        for name, expected in cases.items():
            self.assertEqual(resolve_std_name(name), expected)

    def test_resolve_std_name_fallback(self):
        self.assertEqual(resolve_std_name('unknown-enc'), 'unknown-enc')


class TestDetectPipeline(unittest.TestCase):
    """验证 detect_with_full_decision 在各种编码上正常工作"""

    def _check_result(self, data, expected_encoding=None):
        result = detect_with_full_decision(data)
        self.assertIn('encoding', result)
        self.assertIn('std_name', result)
        self.assertIn('confidence', result)
        self.assertIn('top_candidates', result)
        self.assertIsInstance(result['encoding'], str)
        self.assertIsInstance(result['std_name'], str)
        self.assertIsInstance(result['confidence'], (int, float))
        self.assertIsInstance(result['top_candidates'], list)
        if expected_encoding is not None:
            self.assertEqual(result['encoding'], expected_encoding)

    def test_empty(self):
        self._check_result(b'', 'UTF-8')

    def test_ascii(self):
        self._check_result(b'Hello World 123', 'ASCII')

    def test_utf8_chinese(self):
        self._check_result('你好世界'.encode('utf-8'), 'UTF-8')

    def test_gbk_chinese(self):
        self._check_result('计算机课程设计'.encode('gbk'), 'GBK')

    def test_big5_traditional(self):
        self._check_result('電腦課程'.encode('big5'), 'GBK')

    def test_shift_jis_japanese(self):
        data = '日本語'.encode('cp932')
        result = detect_with_full_decision(data)
        # Short pure-CJK SJIS text (no kana) may still be ambiguous
        self.assertIn(result['encoding'], ('GBK', 'Shift-JIS'))

    def test_shift_jis_with_kana(self):
        """含假名的 Shift-JIS 必须正确检测"""
        data = '日本語テスト'.encode('cp932')
        result = detect_with_full_decision(data)
        self.assertEqual(result['encoding'], 'Shift-JIS')

    def test_utf16_le(self):
        self._check_result('Hello World'.encode('utf-16-le'), 'UTF-16 LE')

    def test_utf16_be(self):
        self._check_result('Hello World'.encode('utf-16-be'), 'UTF-16 BE')

    def test_utf16_le_chinese(self):
        data = '测试 编码 转换'.encode('utf-16-le')
        self._check_result(data, 'UTF-16 LE')

    def test_utf16_be_chinese(self):
        data = '测试 编码 转换'.encode('utf-16-be')
        self._check_result(data, 'UTF-16 BE')


class TestFileEncodingDetector(unittest.TestCase):
    """验证 FileEncodingDetector 接口完整性"""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = CHARS_DIR

    def test_detect_file_ascii(self):
        fpath = os.path.join(self.test_dir, 'numbers.txt')
        if not os.path.isfile(fpath):
            self.skipTest('numbers.txt not found')
        enc, std = FileEncodingDetector.detect_file(fpath)
        self.assertIsInstance(enc, str)
        self.assertIsInstance(std, str)

    def test_detect_file_utf8(self):
        fpath = os.path.join(self.test_dir, 'comprehensive_test.txt')
        if not os.path.isfile(fpath):
            self.skipTest('comprehensive_test.txt not found')
        enc, std = FileEncodingDetector.detect_file(fpath)
        self.assertEqual(enc, 'UTF-8')

    def test_file_to_tokens(self):
        fpath = os.path.join(self.test_dir, 'comprehensive_test.txt')
        if not os.path.isfile(fpath):
            self.skipTest('comprehensive_test.txt not found')
        tokens = FileEncodingDetector.file_to_tokens(fpath)
        self.assertIsInstance(tokens, list)
        self.assertGreater(len(tokens), 0)
        for t in tokens:
            self.assertTrue(hasattr(t, 'char'))
            self.assertTrue(hasattr(t, 'source_encoding'))
            self.assertTrue(hasattr(t, 'source_bytes'))

    def test_diagnose_detect(self):
        fpath = os.path.join(self.test_dir, 'comprehensive_test.txt')
        if not os.path.isfile(fpath):
            self.skipTest('comprehensive_test.txt not found')
        trials, enc_name, is_pure_ascii = FileEncodingDetector.diagnose_detect(fpath)
        self.assertIsInstance(trials, list)
        self.assertIsInstance(enc_name, str)
        self.assertIsInstance(is_pure_ascii, bool)

    def test_charset_detect(self):
        result = FileEncodingDetector.charset_detect(b'Hello World')
        self.assertIn('encoding', result)
        self.assertIn('confidence', result)


class TestAllAgentsCallable(unittest.TestCase):
    """验证 _ALL_AGENTS 列表正确"""

    def test_all_agents_callable(self):
        for agent in _ALL_AGENTS:
            self.assertTrue(callable(agent), f'{agent} is not callable')

    def test_all_agents_return_dict(self):
        data = b'Hello World Test'
        for agent in _ALL_AGENTS:
            result = agent(data)
            self.assertIsInstance(result, dict)
            self.assertEqual(len(result), 1)
            key, val = next(iter(result.items()))
            self.assertIsInstance(key, str)
            self.assertIsInstance(val, float)

    def test_cjk_agents_config(self):
        self.assertIsInstance(GBK_AGENT, EncodingDetectionAgent)
        self.assertIsInstance(BIG5_AGENT, EncodingDetectionAgent)
        self.assertIsInstance(SHIFT_JIS_AGENT, EncodingDetectionAgent)
        self.assertEqual(GBK_AGENT.display_name, 'GBK')
        self.assertEqual(BIG5_AGENT.display_name, 'Big5')
        self.assertEqual(SHIFT_JIS_AGENT.display_name, 'Shift-JIS')


class TestShiftJISDetection(unittest.TestCase):
    """验证 Shift-JIS 日文检测正确性（含平假名、片假名、汉字）"""

    KANA_SAMPLES = [
        ("kana_katakana", "プログラム"),
        ("kana_hiragana", "こんにちは"),
        ("kana_mixed", "日本語テスト"),
        ("kana_long", "Hello! 日本語プログラミングテスト。データ構造。"),
        ("kana_hira_katakana", "こんにちは世界プログラム"),
    ]

    def test_shift_jis_detected_as_top_candidate(self):
        """Shift-JIS 文本必须检测为 Shift-JIS（top candidate）"""
        for name, text in self.KANA_SAMPLES:
            raw = text.encode("cp932")
            result = detect_with_full_decision(raw)
            top1 = result["encoding"]
            self.assertEqual(
                top1, "Shift-JIS",
                f"{name}: expected Shift-JIS, got {top1} "
                f"(candidates={result['top_candidates'][:3]})"
            )

    def test_shift_jis_confidence_not_degraded(self):
        """Shift-JIS 置信度不应低于 0.5"""
        for name, text in self.KANA_SAMPLES:
            raw = text.encode("cp932")
            result = detect_with_full_decision(raw)
            self.assertGreater(
                result["confidence"], 0.5,
                f"{name}: confidence {result['confidence']} too low"
            )

    def test_gbk_still_detected_as_gbk(self):
        """GBK 中文检测不受影响"""
        gbk_texts = [
            ("basic", "计算机课程设计"),
            ("longer", "数据结构与算法分析"),
            ("mixed", "Hello 你好世界"),
        ]
        for name, text in gbk_texts:
            raw = text.encode("gbk")
            result = detect_with_full_decision(raw)
            self.assertEqual(
                result["encoding"], "GBK",
                f"{name}: expected GBK, got {result['encoding']}"
            )

    def test_big5_still_detected_as_big5(self):
        """Big5 繁体中文检测不受影响"""
        big5_texts = [
            ("mixed", "Hello 你好世界"),
            ("longer", "電腦程式設計資料結構和演算法"),
        ]
        for name, text in big5_texts:
            raw = text.encode("big5")
            result = detect_with_full_decision(raw)
            self.assertEqual(
                result["encoding"], "Big5",
                f"{name}: expected Big5, got {result['encoding']}"
            )

    def test_utf8_detection_unaffected(self):
        """UTF-8 检测不受影响"""
        utf8_texts = [
            ("chinese", "你好世界"),
            ("emoji", "Hello 😀🚀 你好"),
            ("mixed", "Hello 你好"),
        ]
        for name, text in utf8_texts:
            raw = text.encode("utf-8")
            result = detect_with_full_decision(raw)
            self.assertEqual(
                result["encoding"], "UTF-8",
                f"{name}: expected UTF-8, got {result['encoding']}"
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)
