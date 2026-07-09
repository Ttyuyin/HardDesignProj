"""
Layer 3: Decision Engine

Softmax normalization, agent orchestration, content-based tie-breaking.
"""

import math
from collections import Counter

from encoding import resolve_std_name
from text_analyzer import char_category

from .agents import _ALL_AGENTS


def _softmax(values: list[float], temperature: float = 10.0) -> list[float]:
    """Compute softmax with shift and temperature scaling."""
    if not values:
        return []
    scaled = [v * temperature for v in values]
    mx = max(scaled)
    shifted = [v - mx for v in scaled]
    exps = [math.exp(v) for v in shifted]
    s = sum(exps) or 1.0
    return [e / s for e in exps]


def _run_agents(raw_data: bytes) -> dict[str, float]:
    """Run all agents and merge their scores."""
    scores: dict[str, float] = {}
    for agent in _ALL_AGENTS:
        scores.update(agent(raw_data))
    return scores


def _content_discriminator(candidates: list[str], raw_data: bytes) -> str | None:
    """Break ties by checking decoded text for unique encoding signals."""
    decoded = {}
    for name in candidates:
        std = resolve_std_name(name)
        try:
            text = raw_data.decode(std, errors="replace")
            cats = Counter(char_category(ord(ch)) for ch in text)
            decoded[name] = (text, cats)
        except Exception:
            continue

    if "Shift-JIS" in decoded:
        _, cats = decoded["Shift-JIS"]
        total = max(1, sum(cats.values()))
        kana_ratio = (cats.get("hiragana", 0) + cats.get("katakana", 0)) / total
        if kana_ratio > 0.02:
            return "Shift-JIS"

    if "Big5" in decoded:
        _, cats = decoded["Big5"]
        total = max(1, sum(cats.values()))
        bpmf_ratio = cats.get("bopomofo", 0) / total
        if bpmf_ratio > 0.02:
            return "Big5"

    best_name = None
    best_score = -1
    for name in candidates:
        if name not in decoded:
            continue
        _, cats = decoded[name]
        total = max(1, sum(cats.values()))
        cjk = cats.get("cjk", 0) / total
        bpmf = cats.get("bopomofo", 0) / total
        score = cjk + bpmf * 0.5
        if score > best_score:
            best_score = score
            best_name = name
    return best_name
