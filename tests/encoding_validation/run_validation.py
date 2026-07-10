"""
Encoding System Validation Report Generator

独立验证体系，不修改任何 src 代码。
使用 Python 标准库进行独立 byte 验证，禁止使用检测器验证自己。

测试流程：
  1. 生成各编码的真实字节样本
  2. 调用检测器（detect_with_full_decision）验证检测准确率
  3. 执行跨编码转换测试
  4. 使用 Python 标准库进行独立 byte 验证（decode + Unicode 比较）
  5. 生成完整报告

输出：tests/encoding_validation/VALIDATION_REPORT.txt
"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# ── 被测试系统：仅用于检测，不用于转换验证 ──
from detector.pipeline import detect_with_full_decision

# ── 报告输出路径 ──
REPORT_PATH = os.path.join(os.path.dirname(__file__), "VALIDATION_REPORT.txt")


# ══════════════════════════════════════════════════════════════════════
# 第 1 阶段：生成真实编码样本
# ══════════════════════════════════════════════════════════════════════

def _make_sample(label, text, encoding, codec):
    """尝试编码生成字节样本，失败时返回 None"""
    try:
        raw = text.encode(codec)
        return {"label": label, "text": text, "encoding": encoding, "codec": codec, "raw": raw, "length": len(raw)}
    except UnicodeEncodeError as e:
        return None


def _sample_texts():
    """候选文本定义"""
    return {
        "ascii": ("ASCII", "ascii",
            "Hello, World! This is a pure ASCII test string with numbers 12345."),

        "utf8": ("UTF-8", "utf-8",
            "Hello World! 你好世界，计算机程序设计。日本語でテスト。"),

        "utf16le": ("UTF-16 LE", "utf-16-le",
            "Hello World! 你好世界，计算机程序设计。"),

        "utf16be": ("UTF-16 BE", "utf-16-be",
            "Hello World! 你好世界，计算机程序设计。"),

        "gb2312": ("GB2312", "gb2312",
            "Hello! 计算机程序设计数据结构和算法。你好世界。"),

        "gbk_ext": ("GBK", "gbk",
            "Hello! 计算机程序设计数据结构算法。你好世界。中文编码转换测试。"),

        "big5": ("Big5", "big5",
            "Hello! 電腦程式設計數據結構演算法。你好世界。"),

        "shiftjis": ("Shift-JIS", "cp932",
            "Hello! 日本語プログラミングテスト。データ構造。"),
    }


def generate_samples():
    """生成所有编码的真实字节样本"""
    samples = []
    errors = []
    for key, (enc, codec, text) in _sample_texts().items():
        result = _make_sample(key, text, enc, codec)
        if result:
            samples.append(result)
        else:
            errors.append(key)
    return samples, errors


# ══════════════════════════════════════════════════════════════════════
# 第 2 阶段：检测测试
# ══════════════════════════════════════════════════════════════════════

def run_detection_tests(samples):
    """对每个样本调用检测器，记录结果"""
    results = []
    for s in samples:
        decision = detect_with_full_decision(s["raw"])
        detected = decision["encoding"]
        confidence = decision["confidence"]
        top = decision["top_candidates"]
        passed = (detected == s["encoding"])
        results.append({
            "label": s["label"],
            "actual_encoding": s["encoding"],
            "detected_encoding": detected,
            "confidence": confidence,
            "top_candidates": top,
            "passed": passed,
            "length": s["length"],
        })
    return results


# ══════════════════════════════════════════════════════════════════════
# 第 3 阶段：转换测试（独立 byte 验证）
# ══════════════════════════════════════════════════════════════════════

# 转换配对定义：(源编码标签, 目标编码标签, 转换场景)
CONVERSION_PAIRS = [
    ("utf8",    "utf16le",  "UTF-8  → UTF-16 LE"),
    ("utf8",    "utf16be",  "UTF-8  → UTF-16 BE"),
    ("utf16le", "utf8",     "UTF-16 LE → UTF-8"),
    ("utf16be", "utf8",     "UTF-16 BE → UTF-8"),
    ("gbk_ext", "big5",     "GBK    → Big5"),
    ("big5",    "gbk_ext",  "Big5   → GBK"),
    ("shiftjis","utf8",     "Shift-JIS → UTF-8"),
    ("utf8",    "shiftjis", "UTF-8  → Shift-JIS"),
    ("shiftjis","gbk_ext",  "Shift-JIS → GBK"),
    ("gbk_ext", "shiftjis", "GBK    → Shift-JIS"),
]


def independent_convert(text, src_codec, tgt_codec, errors="replace"):
    """使用 Python 标准库进行独立转换验证

    流程：
      1. 用 src_codec 将 text 编码为源字节
      2. 用 tgt_codec 将 text 编码为目标字节
      3. 用 tgt_codec 解码目标字节回 Unicode
      4. 逐字符比较并统计损失

    返回 dict 包含完整的转换验证信息。
    """
    source_bytes = text.encode(src_codec, errors="strict")

    # 执行转换：text → target_bytes
    target_bytes = text.encode(tgt_codec, errors=errors)

    # 独立验证：用目标编码解码回 Unicode
    recovered_text = target_bytes.decode(tgt_codec, errors="replace")

    # 逐字符比较
    lossy_chars = []
    for i, (orig, recov) in enumerate(zip(text, recovered_text)):
        if orig != recov:
            lossy_chars.append({
                "position": i,
                "original": orig,
                "original_cp": f"U+{ord(orig):04X}",
                "recovered": recov,
                "recovered_cp": f"U+{ord(recov):04X}" if recov != '\ufffd' else "U+FFFD",
            })

    # 检查不可转换字符（从 Unicode 角度看）
    unencodable = []
    for i, ch in enumerate(text):
        try:
            ch.encode(tgt_codec, errors="strict")
        except UnicodeEncodeError:
            unencodable.append({
                "position": i,
                "char": ch,
                "codepoint": f"U+{ord(ch):04X}",
            })

    return {
        "source_bytes": source_bytes,
        "target_bytes": target_bytes,
        "recovered_text": recovered_text,
        "lossless": (text == recovered_text and len(text) == len(recovered_text)),
        "total_chars": len(text),
        "match_count": sum(1 for a, b in zip(text, recovered_text) if a == b),
        "lossy_chars": lossy_chars,
        "unencodable_count": len(unencodable),
        "unencodable_chars": unencodable,
        "recovered_length": len(recovered_text),
    }


def run_conversion_tests(samples_by_key):
    """运行所有转换配对的独立验证测试"""
    results = []
    for src_key, tgt_key, description in CONVERSION_PAIRS:
        src = samples_by_key.get(src_key)
        tgt_enc_name = _sample_texts()[tgt_key][0]
        tgt_codec = _sample_texts()[tgt_key][1]

        if src is None:
            results.append({
                "pair": description,
                "src_key": src_key,
                "tgt_key": tgt_key,
                "error": f"Source sample '{src_key}' not available",
                "lossless": False,
            })
            continue

        text = src["text"]

        # 用于判定，使用目标编码的 codec
        result = independent_convert(text, src["codec"], tgt_codec)
        result["pair"] = description
        result["src_encoding"] = src["encoding"]
        result["tgt_encoding"] = tgt_enc_name
        results.append(result)
    return results


# ══════════════════════════════════════════════════════════════════════
# 第 4 阶段：分析
# ══════════════════════════════════════════════════════════════════════

def analyze_ambiguous_cases(detection_results):
    """分析模糊判定案例"""
    ambiguous = []
    for r in detection_results:
        top = r["top_candidates"]
        if len(top) >= 2:
            gap = top[0][1] - top[1][1]
            if gap < 0.05:
                ambiguous.append({
                    "label": r["label"],
                    "actual": r["actual_encoding"],
                    "detected": r["detected_encoding"],
                    "gap": round(gap, 4),
                    "top": [(n, round(p, 4)) for n, p in top[:3]],
                })
    return ambiguous


def analyze_lossy(conversion_results):
    """分析有损转换案例"""
    lossy = []
    for r in conversion_results:
        if r.get("error"):
            continue
        if not r["lossless"]:
            lossy.append({
                "pair": r["pair"],
                "total": r["total_chars"],
                "match": r["match_count"],
                "unencodable": r["unencodable_count"],
                "lossy_chars": r["lossy_chars"][:10],  # 最多显示 10 个
                "all_lossy_chars": r["lossy_chars"],
            })
    return lossy


# ══════════════════════════════════════════════════════════════════════
# 第 5 阶段：报告生成
# ══════════════════════════════════════════════════════════════════════

SEP = "=" * 78
SEP2 = "-" * 78


def fmt_header(title):
    return f"\n{SEP}\n{title}\n{SEP}"


def fmt_subheader(title):
    return f"\n{SEP2}\n{title}\n{SEP2}"


def generate_report(detection_results, conversion_results, sample_errors,
                    ambiguous, lossy_list):
    """生成完整验证报告"""
    lines = []
    L = lines.append

    L(fmt_header("Encoding System Validation Report"))
    L(f"Date: 2026-07-10")
    L(f"Detector: detect_with_full_decision (3-Layer Pipeline)")
    L(f"Samples Generated: {len(detection_results)}")
    L(f"Sample Errors: {len(sample_errors)} ({', '.join(sample_errors) if sample_errors else 'none'})")
    L(f"Conversion Pairs Tested: {len(conversion_results)}")

    # ── 1. Detection Accuracy Table ──
    L(fmt_header("1. Detection Accuracy Table"))
    L(f"{'Sample':<14} {'Actual':<14} {'Detected':<14} {'Conf':<8} {'Pass':<6} Length")
    L(SEP2)
    for r in detection_results:
        L(f"{r['label']:<14} {r['actual_encoding']:<14} {r['detected_encoding']:<14} "
          f"{r['confidence']:<8.4f} {'OK' if r['passed'] else 'FAIL':<6} {r['length']}")

    pass_count = sum(1 for r in detection_results if r['passed'])
    fail_count = sum(1 for r in detection_results if not r['passed'])
    total = len(detection_results)
    accuracy = pass_count / total * 100 if total > 0 else 0
    L(f"\nAccuracy: {pass_count}/{total} = {accuracy:.1f}%")

    if fail_count > 0:
        L(f"\nFAILURES:")
        for r in detection_results:
            if not r['passed']:
                top_str = ", ".join(f"{n}({p:.3f})" for n, p in r['top_candidates'][:3])
                L(f"  {r['label']}: actual={r['actual_encoding']}, "
                  f"detected={r['detected_encoding']}, top={top_str}")

    # ── 2. Top Candidates Detail ──
    L(fmt_header("2. Top Candidates Detail"))
    for r in detection_results:
        L(f"\n{r['label']} ({r['actual_encoding']}, {r['length']} bytes):")
        for name, prob in r['top_candidates']:
            marker = " <<<" if name == r['actual_encoding'] else ""
            L(f"  {name:<16} {prob:.4f}{marker}")

    # ── 3. Conversion Verification Table ──
    L(fmt_header("3. Conversion Verification Table"))
    L(f"{'Pair':<32} {'Lossless':<10} {'Match/Total':<16} {'Lossy':<8} Error")
    L(SEP2)
    for r in conversion_results:
        if r.get("error"):
            L(f"{r['pair']:<32} {'N/A':<10} {'N/A':<16} {'N/A':<8} {r['error']}")
        else:
            lossless = "YES" if r['lossless'] else "NO"
            lossy_n = len(r.get("lossy_chars", []))
            mt = f"{r['match_count']}/{r['total_chars']}"
            L(f"{r['pair']:<32} {lossless:<10} {mt:<16} {lossy_n:<8}")

    lossless_count = sum(1 for r in conversion_results if not r.get("error") and r.get("lossless"))
    total_conversions = sum(1 for r in conversion_results if not r.get("error"))
    if total_conversions > 0:
        L(f"\nLossless Conversions: {lossless_count}/{total_conversions}")

    # ── 4. Byte Difference Analysis ──
    L(fmt_header("4. Byte Difference Analysis"))
    L("Comparing source bytes vs target bytes for each conversion pair:")
    for r in conversion_results:
        if r.get("error"):
            continue
        src_bytes = r.get("source_bytes", b"")
        tgt_bytes = r.get("target_bytes", b"")
        L(f"\n  {r['pair']}:")
        L(f"    Source ({r['src_encoding']}): {len(src_bytes)} bytes -> {src_bytes[:40].hex()}{'...' if len(src_bytes) > 40 else ''}")
        L(f"    Target ({r['tgt_encoding']}): {len(tgt_bytes)} bytes -> {tgt_bytes[:40].hex()}{'...' if len(tgt_bytes) > 40 else ''}")
        ratio = len(tgt_bytes) / max(1, len(src_bytes))
        L(f"    Size ratio: {ratio:.2f}x ({len(tgt_bytes)} / {len(src_bytes)})")

    # ── 5. Lossy Conversion Analysis ──
    L(fmt_header("5. Lossy Conversion Analysis"))
    if lossy_list:
        L(f"\nFound {len(lossy_list)} lossy conversions:")
        for lr in lossy_list:
            L(f"\n  {lr['pair']}:")
            L(f"    Total chars: {lr['total']}, Matched: {lr['match']}, "
              f"Unencodable: {lr['unencodable']}")
            if lr['lossy_chars']:
                L(f"    Lossy transitions (first {len(lr['lossy_chars'])}):")
                for lc in lr['lossy_chars']:
                    L(f"      [{lc['position']}] {lc['original']} "
                      f"({lc['original_cp']}) -> {lc['recovered']} ({lc['recovered_cp']})")
    else:
        L("\nNo lossy conversions detected.")

    # ── 6. Ambiguous Cases ──
    L(fmt_header("6. Ambiguous Cases (gap < 5%)"))
    if ambiguous:
        L(f"\nFound {len(ambiguous)} ambiguous detection(s):")
        for a in ambiguous:
            top_str = ", ".join(f"{n}({p})" for n, p in a["top"])
            L(f"  {a['label']}: actual={a['actual']}, detected={a['detected']}, "
              f"gap={a['gap']:.4f}, top={top_str}")
    else:
        L("\nNo ambiguous detections.")

    # ── 7. Final Recommendation ──
    L(fmt_header("7. Final Recommendation"))

    overall_verdict = "PASS" if fail_count == 0 else "FAIL"
    conversion_verdict = "PASS" if lossless_count == total_conversions else "WARNING"

    L(f"\nDetection Accuracy: {accuracy:.1f}% ({pass_count}/{total})")
    L(f"Lossless Conversion Rate: {lossless_count}/{total_conversions}")
    L(f"Ambiguous Detections: {len(ambiguous)}")
    L(f"Lossy Conversions: {len(lossy_list)}")

    L(f"\nOverall Verdict: {overall_verdict}")

    if fail_count > 0:
        L("\nIssues Found:")
        for r in detection_results:
            if not r['passed']:
                L(f"  - {r['label']}: detected as {r['detected_encoding']} "
                  f"(expected {r['actual_encoding']})")

    if lossy_list:
        L("\nConversion Recommendations:")
        for lr in lossy_list:
            L(f"  - {lr['pair']}: {lr['match']}/{lr['total']} chars survived. "
              f"{lr['unencodable']} chars could not be represented in target encoding.")

    L(f"\nNote: This report was generated using Python stdlib for independent byte verification.")
    L(f"The detector (detect_with_full_decision) was only used for detection scoring, not for conversion validation.")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("Encoding System Validation — Generating Report")
    print("=" * 70)

    # Phase 1: Generate samples
    print("\n[Phase 1] Generating encoding samples...")
    samples, sample_errors = generate_samples()
    samples_by_key = {s["label"]: s for s in samples}

    for s in samples:
        print(f"  OK  {s['label']:<12} {s['encoding']:<14} {s['length']:>6} bytes")
    for e in sample_errors:
        print(f"  ERR {e:<12} FAILED TO GENERATE")

    # Phase 2: Detection tests
    print(f"\n[Phase 2] Running detection tests ({len(samples)} samples)...")
    detection_results = run_detection_tests(samples)
    for r in detection_results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  {status:4s} {r['label']:<12} actual={r['actual_encoding']:<14} "
              f"detected={r['detected_encoding']:<14} conf={r['confidence']:.4f}")

    # Phase 3: Conversion tests
    print(f"\n[Phase 3] Running conversion tests ({len(CONVERSION_PAIRS)} pairs)...")
    conversion_results = run_conversion_tests(samples_by_key)
    for r in conversion_results:
        if r.get("error"):
            print(f"  ERR   {r['pair']:<32} {r['error']}")
        else:
            ls = "LOSS LESS" if r.get("lossless") else "LOSSY"
            print(f"  {ls:9s} {r['pair']:<32} "
                  f"{r['match_count']}/{r['total_chars']} "
                  f"({r.get('unencodable_count', 0)} unencodable)")

    # Analysis
    ambiguous = analyze_ambiguous_cases(detection_results)
    lossy_list = analyze_lossy(conversion_results)

    # Generate report
    print(f"\n[Phase 4] Generating report...")
    report = generate_report(
        detection_results, conversion_results, sample_errors,
        ambiguous, lossy_list
    )

    # Write report
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    # Print summary
    print(f"\n{'=' * 70}")
    pass_count = sum(1 for r in detection_results if r['passed'])
    total = len(detection_results)
    print(f"Detection Accuracy: {pass_count}/{total} ({pass_count/total*100:.1f}%)")
    lossless_count = sum(1 for r in conversion_results if not r.get("error") and r.get("lossless"))
    total_conv = sum(1 for r in conversion_results if not r.get("error"))
    print(f"Lossless Conversions: {lossless_count}/{total_conv}")
    print(f"Report saved to: {REPORT_PATH}")
    print(f"{'=' * 70}")

    return report


if __name__ == "__main__":
    main()
