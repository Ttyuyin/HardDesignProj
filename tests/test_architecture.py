"""
架构约束测试 —— 确保重构后各层职责清晰
- pipeline.py 纯编排，不包含评分/决策逻辑
- anchors.py 只提供证据
- agents.py 只产生评分
- decision.py 做最终决策
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


class TestPipelineArchitecture(unittest.TestCase):
    """验证 pipeline.py 纯粹编排，不参与评分和决策"""

    def setUp(self):
        with open(Path(__file__).resolve().parent.parent / "src" / "detector" / "pipeline.py", encoding="utf-8") as f:
            self.source = f.read()

    def test_no_softmax_in_pipeline(self):
        self.assertNotIn("_softmax", self.source,
                         "pipeline 不应包含 softmax 逻辑")

    def test_no_content_discriminator_in_pipeline(self):
        self.assertNotIn("_content_discriminator", self.source,
                         "pipeline 不应包含内容裁决逻辑")

    def test_no_score_modification_in_pipeline(self):
        """pipeline 不应直接修改 Agent 输出的分数（如 scores['UTF-16 LE'] = ...）"""
        self.assertNotIn("scores[", self.source,
                         "pipeline 不应修改 scores")

    def test_no_softmax_import_in_pipeline(self):
        self.assertNotIn("_softmax", self.source,
                         "pipeline 不应 import _softmax")

    def test_no_content_discriminator_import_in_pipeline(self):
        self.assertNotIn("_content_discriminator", self.source,
                         "pipeline 不应 import _content_discriminator")

    def test_pipeline_imports_from_agents(self):
        self.assertIn("from .agents import", self.source,
                      "pipeline 应从 agents 导入")

    def test_pipeline_calls_decide(self):
        self.assertIn("decide(", self.source,
                      "pipeline 应调用 decide()")

    def test_pipeline_calls_run_anchors(self):
        self.assertIn("run_anchors(", self.source,
                      "pipeline 应调用 run_anchors()")

    def test_pipeline_calls_run_agents(self):
        self.assertIn("run_agents(", self.source,
                      "pipeline 应调用 run_agents()")


class TestAnchorsArchitecture(unittest.TestCase):
    """验证 anchors.py 只提供证据，不做判定"""

    def setUp(self):
        with open(Path(__file__).resolve().parent.parent / "src" / "detector" / "anchors.py", encoding="utf-8") as f:
            self.source = f.read()

    def test_no_softmax_in_anchors(self):
        self.assertNotIn("softmax", self.source,
                         "anchors 不应包含 softmax")

    def test_no_decision_ranking_in_anchors(self):
        """anchors 不应包含 top_candidates 等决策阶段的产物"""
        self.assertNotIn("top_candidates", self.source,
                         "anchors 不应包含排名结果")

    def test_run_anchors_returns_dict_with_bom_field(self):
        from detector.anchors import run_anchors
        result = run_anchors(b"Hello World")
        self.assertIn("bom", result)
        self.assertIn("is_ascii", result)
        self.assertIn("utf16_hint", result)

    def test_bom_anchor_returns_dict(self):
        from detector.anchors import _bom_anchor
        result = _bom_anchor(b"\xff\xfeH\x00e\x00")
        self.assertIsNotNone(result)
        self.assertIn("encoding", result)
        self.assertEqual(result["confidence"], 1.0)

    def test_utf16_hint_is_strength_not_assertion(self):
        from detector.anchors import run_anchors
        result = run_anchors(b"\x00H\x00e\x00l\x00l\x00o")
        self.assertIn("utf16_hint", result)
        hint = result["utf16_hint"]
        self.assertIn("endian", hint)
        self.assertIn("hint_strength", hint)
        # 如果 hint_strength > 0，端序不应为 None
        if hint["hint_strength"] > 0:
            self.assertIsNotNone(hint["endian"])


class TestAgentsArchitecture(unittest.TestCase):
    """验证 agents.py 只产生评分，不做决策"""

    def setUp(self):
        with open(Path(__file__).resolve().parent.parent / "src" / "detector" / "agents.py", encoding="utf-8") as f:
            self.source = f.read()

    def test_no_softmax_in_agents(self):
        self.assertNotIn("softmax", self.source,
                         "agents 不应包含 softmax")

    def test_no_decision_in_agents(self):
        self.assertNotIn("top_candidates", self.source,
                         "agents 不应包含 top_candidates")

    def test_run_agents_accepts_anchors(self):
        from detector.agents import run_agents
        anchors = {"utf16_hint": {"endian": "BE", "hint_strength": 0.5}}
        scores = run_agents(b"Hello", anchors)
        self.assertIsInstance(scores, dict)

    def test_utf16_agents_use_anchor_hint(self):
        from detector.agents import _utf16le_agent, _utf16be_agent
        data = b"\x00H\x00e\x00l\x00l\x00o"
        anchors = {"utf16_hint": {"endian": "BE", "hint_strength": 0.8}}
        score_le = _utf16le_agent(data, anchors)["UTF-16 LE"]
        score_be = _utf16be_agent(data, anchors)["UTF-16 BE"]
        # BE 有 hint 加成，应该不低于 LE
        self.assertGreaterEqual(score_be, score_le * 0.5,
                                "BE agent 在 BE hint 下不应远低于 LE")


class TestDecisionArchitecture(unittest.TestCase):
    """验证 decision.py 做最终决策"""

    def test_decide_returns_full_result(self):
        from detector.decision import decide
        scores = {"UTF-8": 0.9, "GBK": 0.3}
        result = decide(scores, b"test data")
        self.assertIn("encoding", result)
        self.assertIn("std_name", result)
        self.assertIn("confidence", result)
        self.assertIn("top_candidates", result)

    def test_softmax_produces_probabilities(self):
        from detector.decision import _softmax
        probs = _softmax([0.8, 0.3, 0.1])
        self.assertAlmostEqual(sum(probs), 1.0)
        self.assertGreater(probs[0], probs[1])

    def test_content_discriminator_only_in_decision(self):
        with open(Path(__file__).resolve().parent.parent / "src" / "detector" / "decision.py", encoding="utf-8") as f:
            source = f.read()
        self.assertIn("_content_discriminator", source,
                      "decision 应包含 content_discriminator")


if __name__ == "__main__":
    unittest.main()
