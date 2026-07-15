"""Layer 3: 决策引擎 —— Softmax 归一化、排序、gap 判断、内容裁决"""

import math
from collections import Counter

from encoding import DETECTION_ORDER, resolve_std_name
from detector.text_analyzer import char_category


def decide(scores: dict[str, float], raw_data: bytes) -> dict:
    """综合 L2 分数，执行 Softmax + 平局裁决，返回最终结果"""
    names = list(scores.keys())
    vals = [scores[n] for n in names]
    probs = _softmax(vals, temperature=10.0)

    ranked = sorted(zip(names, probs), key=lambda x: x[1], reverse=True)

    if not ranked:
        return {
            "encoding": "UTF-8",
            "std_name": "utf-8",
            "confidence": 0.5,
            "top_candidates": [],
        }

    winner_name, winner_prob = _resolve_winner(ranked, scores, raw_data)

    std_name = resolve_std_name(winner_name)
    return {
        "encoding": winner_name,
        "std_name": std_name,
        "confidence": round(winner_prob, 4),
        "top_candidates": [(n, round(p, 4)) for n, p in ranked],
    }


def _softmax(values: list[float], temperature: float = 10.0) -> list[float]:
    """带温度参数和数值移位的 Softmax 归一化"""
    if not values:
        return []
    scaled = [v * temperature for v in values]
    mx = max(scaled)
    shifted = [v - mx for v in scaled]
    exps = [math.exp(v) for v in shifted]
    s = sum(exps) or 1.0
    return [e / s for e in exps]


def _resolve_winner(ranked, raw_scores, raw_data):
    """当 top-2 差距 < 5% 时进入内容二次裁决，否则直接返回"""
    top1_name, top1_prob = ranked[0]
    top2_prob = ranked[1][1] if len(ranked) > 1 else 0.0
    gap = top1_prob - top2_prob

    if gap < 0.05 and len(ranked) > 1:
        det_names = {enc.display_name for enc in DETECTION_ORDER}
        tied = [
            name for name, prob in ranked
            if top1_prob - prob < 0.05 and name in det_names
        ]

        if len(tied) >= 2:
            winner = _content_discriminator(tied, raw_data)
            if winner:
                return winner, top1_prob
            for enc in DETECTION_ORDER:
                if enc.display_name in tied:
                    return enc.display_name, top1_prob
        elif len(tied) == 1:
            return tied[0], top1_prob
        else:
            if raw_scores.get("UTF-8", 0) > 0.5:
                return "UTF-8", top1_prob

    return top1_name, top1_prob


def _content_discriminator(candidates: list[str], raw_data: bytes) -> str | None:
    """通过假名/注音符号等唯一编码特征裁决平局"""
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
