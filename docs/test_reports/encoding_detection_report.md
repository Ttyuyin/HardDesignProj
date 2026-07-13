# 编码检测测试报告

| 项目 | 内容 |
|------|------|
| 测试日期 | 2026-07-13 |
| Python 版本 | 3.14.3 |
| 测试样本数 | 15 个文件 |
| 测试工具 | FileEncodingDetector + charset-normalizer 交叉验证 |

---

## 检测样本清单

| # | 文件名 | 真实编码 | 文件大小 |
|:-:|--------|---------|:-------:|
| 1 | `01_ascii.txt` | ASCII | 50 B |
| 2 | `02_utf8_chinese.txt` | UTF-8 | 99 B |
| 3 | `03_utf16le.txt` | UTF-16 LE (BOM) | 106 B |
| 4 | `04_utf16be.txt` | UTF-16 BE (BOM) | 106 B |
| 5 | `05_gbk_chinese.txt` | GBK | 69 B |
| 6 | `06_big5_traditional.txt` | Big5 | 62 B |
| 7 | `07_shiftjis_japanese.txt` | Shift-JIS | 77 B |
| 8 | `french_chars.txt` | UTF-8 | 422 B |
| 9 | `gbk短.txt` | UTF-8 | 18 B |
| 10 | `gbk长.txt` | UTF-8 | 676 B |
| 11 | `korean_chars.txt` | UTF-8 | 699 B |
| 12 | `conversion_cases/case1_utf8_to_gbk.txt` | UTF-8 | 50 B |
| 13 | `conversion_cases/case2_big5_to_gbk.txt` | Big5 | 43 B |
| 14 | `conversion_cases/case3_shiftjis_to_utf8.txt` | Shift-JIS | 48 B |
| 15 | `conversion_cases/case4_utf16_to_utf8.txt` | UTF-16 LE | 90 B |

---

## 检测结果表

| 真实编码 | 测试文件 | 检测结果 | Confidence | 正确 | 错误原因分析 |
|---------|---------|---------|:---------:|:----:|-------------|
| ASCII | 01_ascii.txt | ASCII | 1.0000 | ✓ | |
| UTF-8 | 02_utf8_chinese.txt | UTF-8 | 0.9974 | ✓ | |
| UTF-16 LE | 03_utf16le.txt | UTF-16 LE | 1.0000 | ✓ | BOM 直接匹配 |
| UTF-16 BE | 04_utf16be.txt | UTF-16 BE | 1.0000 | ✓ | BOM 直接匹配 |
| GBK | 05_gbk_chinese.txt | GBK | 0.8352 | ✓ | |
| Big5 | 06_big5_traditional.txt | Big5 | 0.8218 | ✓ | |
| Shift-JIS | 07_shiftjis_japanese.txt | Shift-JIS | 0.4535 | ✓ | 与 GBK 竞争激烈 (GBK 0.4535, S-JIS 0.4261)，内容裁决胜出 |
| UTF-8 | french_chars.txt | UTF-8 | 0.9977 | ✓ | |
| UTF-8 | gbk短.txt | UTF-8 | 0.9995 | ✓ | |
| UTF-8 | gbk长.txt | UTF-8 | 0.9979 | ✓ | |
| UTF-8 | korean_chars.txt | UTF-8 | 0.9981 | ✓ | |
| UTF-8 | case1_utf8_to_gbk.txt | UTF-8 | 0.9979 | ✓ | |
| Big5 | case2_big5_to_gbk.txt | GBK | 0.7042 | ✗ | 小样本 (43 B)，GBK 字节范围覆盖更广导致误判 |
| Shift-JIS | case3_shiftjis_to_utf8.txt | GBK | 0.7413 | ✗ | 小样本 (48 B)，GBK Agent 评分高于 Shift-JIS Agent |
| UTF-16 LE | case4_utf16_to_utf8.txt | UTF-16 LE | 1.0000 | ✓ | BOM 匹配 |

---

## 统计汇总

| 指标 | 数值 |
|------|:---:|
| 总测试样本 | 15 |
| 正确检测 | **13** |
| 错误检测 | **2** |
| **检测准确率** | **86.67%** |
| 高置信度 (>=0.8) | 12 / 15 (80.0%) |
| BOM 样本准确率 | 3 / 3 (100%) |
| 非 BOM 样本准确率 | 10 / 12 (83.3%) |

---

## 错误分析

两次检测失败均发生在 `conversion_cases/` 目录下的小样本文件：

| 文件 | 真实编码 | 检测结果 | 分析 |
|------|---------|---------|------|
| case2_big5_to_gbk.txt (43 B) | Big5 | GBK | 文件过小（仅 43 字节），Big5 与 GBK 字节范围高度重叠，Byte Validator 中 GBK 的前导字节范围 (0x81-0xFE) 覆盖了 Big5 的全部前导字节 (0xA1-0xF9)，导致 GBK 评分更高 |
| case3_shiftjis_to_utf8.txt (48 B) | Shift-JIS | GBK | 同上，小样本使得 GBK Agent 的 byte_score 占优（40% 权重），且 Shift-JIS 的半角片假名特征在小样本中未能充分体现 |

**根本原因**：CJK 多字节编码（GBK/Big5/Shift-JIS）的字节范围存在大面积重叠，在样本 < 50 字节时统计特征不足以可靠区分。此为编码检测领域的固有难题。

---

## 检测流水线分析

```
Layer 1 (锚点) → BOM / ASCII / UTF-16 结构
  ↓ 100% 准确，确定性规则
Layer 2 (Agent 评分) → UTF-8 / GBK / Big5 / Shift-JIS / UTF-16 LE/BE / Extended ASCII
  ↓ 各 Agent 独立评分，0.0 ~ 1.0
Layer 3 (决策) → Softmax → 稳定性规则 → 内容裁决 → 优先级排序
  ↓ temperature=10.0 使分布平坦化，防过拟合
最终判定
```

- Layer 1 (BOM/ASCII 锚点)：**100% 可靠**，无需统计评分
- Layer 2 (Agent 评分)：CJK Agent 的权重配置合理，但对 < 50 B 样本区分力不足
- Layer 3 (内容裁决)：成功解决了 Shift-JIS 和 GBK 的平局问题（通过 kana ratio 检测）

---

## 结论

系统编码检测功能总体表现良好，准确率达 **86.67%**。BOM 检测和 ASCII 快速判定达到 100% 准确率。主要局限在于小样本 CJK 编码的区分，建议在实际使用中确保文件不少于 100 字节以获得更可靠的检测结果。
