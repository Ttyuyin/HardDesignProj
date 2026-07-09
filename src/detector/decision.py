"""
Layer 3: 决策引擎（编码判定层）

Softmax 归一化、Agent 编排、基于文本内容的平局裁决。
接收 Layer 2 各 Agent 的置信度分数，经过归一化和规则判定，
输出最终的编码判定结果。
"""

import math
from collections import Counter

from encoding import resolve_std_name
from text_analyzer import char_category

from .agents import _ALL_AGENTS


def _softmax(values: list[float], temperature: float = 10.0) -> list[float]:
    """带温度参数和数值移位的 Softmax 归一化。

    温度参数 temperature 的作用：
    - temperature > 1：增大 softmax 输出的"平坦度"，使各候选编码的概率分布更均匀，
      避免某个 Agent 的轻微领先被过度放大（本系统使用 10.0）
    - temperature = 1：标准 softmax
    - temperature < 1：放大差异，使高分者得分更高

    数值移位（减去最大值）用于防止 exp 溢出。
    """
    if not values:
        return []
    scaled = [v * temperature for v in values]
    mx = max(scaled)
    shifted = [v - mx for v in scaled]       # 数值移位，保证最大指数项为 exp(0) = 1
    exps = [math.exp(v) for v in shifted]
    s = sum(exps) or 1.0
    return [e / s for e in exps]


def _run_agents(raw_data: bytes) -> dict[str, float]:
    """遍历运行所有 Agent，合并各编码的置信度分数。"""
    scores: dict[str, float] = {}
    for agent in _ALL_AGENTS:
        scores.update(agent(raw_data))
    return scores


def _content_discriminator(candidates: list[str], raw_data: bytes) -> str | None:
    """通过解码文本中的唯一编码信号进行平局裁决。

    当 softmax 后前两名差距 < 5% 时触发此函数。
    利用各编码独有的字符特征区进行二次鉴定：
    - Shift-JIS：检查是否含有平假名/片假名（kana ratio > 2%）
    - Big5：检查是否含有注音符号（bopomofo ratio > 2%）
    - 兜底策略：对比 CJK 统一表意文字比率 + 注音符号比率加权和
    """
    decoded = {}
    for name in candidates:
        std = resolve_std_name(name)
        try:
            text = raw_data.decode(std, errors="replace")
            cats = Counter(char_category(ord(ch)) for ch in text)
            decoded[name] = (text, cats)
        except Exception:
            continue

    # Shift-JIS 特有信号：假名（平假名 + 片假名）
    if "Shift-JIS" in decoded:
        _, cats = decoded["Shift-JIS"]
        total = max(1, sum(cats.values()))
        kana_ratio = (cats.get("hiragana", 0) + cats.get("katakana", 0)) / total
        if kana_ratio > 0.02:
            return "Shift-JIS"

    # Big5 特有信号：注音符号
    if "Big5" in decoded:
        _, cats = decoded["Big5"]
        total = max(1, sum(cats.values()))
        bpmf_ratio = cats.get("bopomofo", 0) / total
        if bpmf_ratio > 0.02:
            return "Big5"

    # 通用兜底：对比 CJK 比率 + 注音符号比率（注音权重减半）
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
