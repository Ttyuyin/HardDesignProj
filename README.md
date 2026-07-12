# 字符编码显示与转换系统

基于 Python 3 + Tkinter 的编码检测、显示、转换工具。支持 GBK / Big5 / Shift-JIS / UTF-8 / UTF-16 等多编码自动识别与互转。

## 快速开始

```powershell
python src/main.py
python -m unittest discover -s tests -p "test_*.py" -v
```

## 目录

- [项目架构](#项目架构)
- [三条核心数据流](#三条核心数据流)
- [编码检测流程（打开文件 → 判断编码）](#一编码检测流程打开文件--判断编码)
- [编码转换流程（UTF-8 → GBK）](#二编码转换流程utf-8--gbk)
- [字符 HEX 查看流程（输入"中"→ 看到各编码字节）](#三字符-hex-查看流程输入中--看到各编码字节)
- [核心评分机制：byte_validator + text_analyzer](#四核心评分机制byte_validator--text_analyzer)
- [7 个评分 Agent](#五7-个评分-agent)
- [文件结构](#文件结构)

---

## 项目架构

```
                 main.py
                    │
              ┌─────▼─────┐
              │   ui/     │  ← Tkinter 界面层
              │  app.py   │     MainWindow
              │  tabs.py  │     两个标签页
              │  tables.py│     Canvas 表格
              │  widgets.py│    图例/按钮工厂
              └─────┬─────┘
                    │
              ┌─────▼─────┐
              │ services/ │  ← Facade 层（GUI 唯一入口）
              │ detector_ │     services/result.py 定义
              │ converter_│     DetectionResult / ConversionResult 等
              └──┬───┬────┘
                 │   │
       ┌─────────▼┐ ┌▼──────────────┐
       │ detector│ │ converter/    │
       │ pipeline│ │ converter.py  │
       │ anchors │ │ verifier.py   │
       │ agents  │ │ compatibility │
       │ decision│ │ converter_    │
       │ byte_   │ │ utils.py      │
       │ validator│ └───────────────┘
       │ text_   │
       │ analyzer│
       │ decode_ │
       │ utils   │
       └─────────┘
           │           │
       ┌───▼───────────▼────┐
       │  shared/           │
       │  encoding.py       │  ← 编码注册中心（唯一数据源）
       │  character_token.py│  ← CharacterToken 数据类
       │  display_utils.py  │  ← bytes_to_hex / codepoint_display
       └────────────────────┘
```

---

## 一、编码检测流程（打开文件 → 判断编码）

### 调用链

```
用户点击"打开文件"
    │
    ▼
ui/tabs.py  ──→  services/detector_service.py  ──→  detector/pipeline.py
 (选文件、调服务)    (diagnose_from_raw)              (FileEncodingDetector)
                                                          │
                                               ┌──────────┼──────────┐
                                               ▼          ▼          ▼
                                        anchors.py  agents.py  decision.py
                                        (Layer 1)   (Layer 2)  (Layer 3)
```

### 三层流水线

| 层 | 文件 | 职责 | 举例 |
|---|------|------|------|
| Layer 1 锚点 | `detector/anchors.py` | 硬规则短路 | BOM(`FF FE`→UTF-16 LE)、纯 ASCII 跳过、UTF-16 null 结构探测 |
| Layer 2 评分 | `detector/agents.py` | 7 个 Agent 独立打分 | 每个 Agent 返回 `{"GBK": 0.85, ...}` |
| Layer 3 决策 | `detector/decision.py` | Softmax + 平局裁决 | 差距 < 5% 时用内容判别器消歧 |

### 检测流程涉及文件

| 文件 | 职责 |
|------|------|
| `ui/tabs.py` | 文件选择、调服务、更新界面 |
| `services/detector_service.py` | 封装检测流程，返回 `DetectionResult` |
| `detector/pipeline.py` | 编排 L1→L2→L3，公开 `FileEncodingDetector` |
| `detector/anchors.py` | BOM / 纯 ASCII / UTF-16 结构判别 |
| `detector/agents.py` | 7 个编码评分 Agent |
| `detector/decision.py` | softmax + 内容消歧 |
| `detector/byte_validator.py` | GBK/Big5/SJIS 字节格式合规评分 |
| `detector/text_analyzer.py` | Unicode 字符分类（CJK/假名/注音） |
| `detector/decode_utils.py` | 统一 `strict_decode` 封装 |
| `shared/character_token.py` | CharacterToken 数据类 |
| `encoding.py` | 编码注册表、检测顺序配置 |

---

## 二、编码转换流程（UTF-8 → GBK）

### 调用链

```
用户点击"执行转换"
    │
    ▼
ui/tabs.py  ──→  services/converter_service.py
 (选编码、策略)      │
                    ├── 1. file_to_tokens() → 解码源文件
                    ├── 2. compatibility_scan() → 预览不可编码字符
                    ├── 3. convert_file() → 执行转换 + 写文件
                    └── 4. verifier.verify_roundtrip() → 验证无损
```

### 转换流程涉及文件

| 文件 | 职责 |
|------|------|
| `ui/tabs.py` | 参数获取、结果展示 |
| `services/converter_service.py` | 编排兼容检查→转换→验证 |
| `converter/compatibility.py` | 转换前预览哪些字符不可编码 |
| `converter/converter.py` | 逐字符 encode 输出 bytes + 写文件 |
| `converter/verifier.py` | 标准库独立解码比对 |
| `converter/converter_utils.py` | `token_target_display` 格式化 |
| `encoding.py` | 编码映射表 |

---

## 三、字符 HEX 查看流程（输入"中"→ 看到各编码字节）

```
用户粘贴文本/打开文件
    │
    ▼
ui/tabs.py ──→ viewer/viewer.py ──→ ui/tables.py
 (获取 tokens)  (EncodingViewer)     (ColoredTable Canvas 表格)
                   │
                   ├── 遍历所有编码：char.encode(std_name)
                   ├── 成功 → bytes_to_hex → "E4 B8 AD"
                   └── 失败 → "N/A"
```

### 查看流程涉及文件

| 文件 | 职责 |
|------|------|
| `viewer/viewer.py` | `EncodingViewer` 逐字符分析各编码字节表示 |
| `ui/tables.py` | `ColoredTable` Canvas 像素级表格 |
| `shared/display_utils.py` | `bytes_to_hex`, `codepoint_display` |
| `encoding.py` | 编码列表、颜色映射 |

---

## 四、核心评分机制：byte_validator + text_analyzer

两把"尺子"配合 `agents.py` 中的 Agent 做综合评判：

| 尺子 | 看什么 | 输入 | 输出 | 核心问题 |
|------|--------|------|------|---------|
| `byte_validator` | **原始字节的编码值**（不关心含义） | `bytes` | 0.0~1.0 格式合规分 | "字节结构像不像 GBK？" |
| `text_analyzer` | **解码后的 Unicode 码点** | `str` | `{cjk_ratio, kana_ratio, ...}` | "解码后是中文、日文还是注音？" |

**为什么需要两层？** 字节范围高度重叠（如 `0xD6 0xD0` 在 GBK 和 Big5 中都合法），只有结合解码后的语言特征才能区分。

**byte_validator 示例：**
```python
score_gbk(b'\xD6\xD0\xB9\xFA')  → 1.0   # 全部字节符合 GBK 格式
score_big5(同一段字节)             → 0.0   # 前导字节不在 Big5 范围内
```
**text_analyzer 示例：**
```python
analyze_text("中国")     → cjk_ratio=1.0,   kana_ratio=0.0, bopomofo=0.0
analyze_text("こんにちは") → cjk_ratio=0.0,   kana_ratio=1.0
analyze_text("ㄅㄆㄇㄈ")   → cjk_ratio=0.0,   bopomofo_ratio=1.0
```

---

## 五、7 个评分 Agent

定义在 `detector/agents.py`，每个 Agent 融合 `byte_validator` 的格式分和 `text_analyzer` 的语言特征分：

| Agent | 评分公式 | 关键区分信号 |
|-------|---------|-------------|
| **UTF-8** | 严格解码 + ASCII 稀释上限 0.5 | 纯 ASCII 不给高分 |
| **GBK** | byte×0.4 + cjk×0.3 + script×0.3 | 汉字权重高，含假名惩罚 |
| **Big5** | byte×0.4 + cjk×0.2 + script×0.2 + **bopomofo×0.2** | 注音符号是 Big5 独有 |
| **Shift-JIS** | byte×0.4 + **kana×0.4** + cjk×0.2 | 假名权重最高 |
| **UTF-16 LE** | null 结构分 + 文本质量 | 奇数位 null 密集 |
| **UTF-16 BE** | null 结构分 + 文本质量 | 偶数位 null 密集 |
| **Extended ASCII** | 固定低分兜底 | ASCII > 95% 给 0.2，否则 0.02 |

7 个分数汇总到 `detector/decision.py`，经 softmax 归一化 + 稳定性规则 + 平局裁决后输出最终编码。

---

## 文件结构

```
src/
├── main.py                    程序入口
│
├── detector/                  检测引擎
│   ├── anchors.py             BOM / 纯 ASCII / UTF-16 结构锚点
│   ├── agents.py              7 个编码评分 Agent
│   ├── decision.py            softmax + 内容消歧
│   ├── pipeline.py            FileEncodingDetector 流水线
│   ├── byte_validator.py      GBK/Big5/SJIS 字节格式评分
│   ├── text_analyzer.py       Unicode 字符分类统计
│   └── decode_utils.py        strict_decode 封装
│
├── converter/                 编码转换引擎
│   ├── converter.py           逐字符 encode + 写文件
│   ├── verifier.py            标准库独立验证往返一致性
│   ├── compatibility.py       转换前不可编码字符预览
│   └── converter_utils.py     token_target_display
│
├── viewer/                    编码查看引擎
│   └── viewer.py              EncodingViewer 逐字符分析
│
├── shared/                    跨领域共享
│   ├── character_token.py     CharacterToken 数据类
│   └── display_utils.py       bytes_to_hex / codepoint_display
│
├── services/                  Facade 层（GUI 唯一入口）
│   ├── result.py              DetectionResult / ConversionResult
│   ├── detector_service.py    检测服务封装
│   └── converter_service.py   转换服务封装
│
├── ui/                        Tkinter 界面层
│   ├── app.py                 MainWindow
│   ├── tabs.py                查看器 + 转换器两个标签页
│   ├── tables.py              ColoredTable / ConversionResultTable
│   └── widgets.py             ColorLegend / 按钮工厂
│
├── encoding.py                编码注册中心（唯一数据源）
├── logs/
└── output/converted/
```

## 演示数据集

`demo_chars/` 包含 11 个编码文件（ASCII / UTF-8 / UTF-16 LE/BE / GBK / Big5 / Shift-JIS 等），用于演示检测与转换功能。详情见 `demo_chars/README.txt`。
