# 字符编码显示与转换系统

基于 Python + Tkinter 的编码检测、显示、转换工具。

## 运行

```powershell
python src/main.py
```

## 测试

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 一、编码检测流程（打开文件 → 判断编码）

用户点击"打开文件"，选择一个 GBK 编码的 txt，系统如何判断出"这是 GBK"？

```
用户点击按钮
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│ ui/tabs.py  (EncodingViewerTab._open_file)                   │
│  弹文件选择框、调用服务、更新界面                                │
│  不知道 GBK/UTF8 怎么判断——只管调服务                            │
└────────────────────────────────┬─────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│ services/detector_service.py  (检测业务门面)                   │
│  diagnose_from_raw() → 读取 bytes + 调用检测器 + 整理结果      │
│  返回 DetectionResult { encoding, std_name, trials }          │
└────────────────────────────────┬─────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│ detector/pipeline.py  (FileEncodingDetector)                  │
│  编排检测流程：anchors → agents → decision                    │
│  detect_with_full_decision()                                  │
└──────────────┬───────────────────────────────────┬───────────┘
               │                                   │
               ▼                                   ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│ detector/anchors.py  (硬规则) │  │ detector/agents.py  (编码评分) │
│                              │  │                              │
│  BOM 探测                    │  │  _utf8_agent()               │
│   FF FE         → UTF-16 LE  │  │   → decode utf-8 + 计算评分   │
│   EF BB BF      → UTF-8      │  │                              │
│                              │  │  GBK_AGENT (EncodingDetectionAgent)
│  纯 ASCII 短路                │  │   → byte_score * 0.4        │
│   所有字节 < 128 → ASCII      │  │   → cjk_ratio * 0.3         │
│                              │  │   → script_score * 0.3       │
│  UTF-16 结构锚点              │  │                              │
│   偶数/奇数 null 比例         │  │  BIG5_AGENT                  │
│                              │  │  SHIFT_JIS_AGENT             │
│  依赖: 无                     │  │  _utf16le_agent              │
│                              │  │  _utf16be_agent              │
│                              │  │  _extended_ascii_agent       │
│                              │  │                              │
│                              │  │  各 agent 返回 {编码: 评分}   │
│                              │  │                              │
│                              │  │  依赖: byte_validator.py     │
│                              │  │        decode_utils.py       │
│                              │  │        text_analyzer.py      │
│                              │  │        encoding.py           │
└──────────────────────────────┘  └──────────────┬───────────────┘
                                                  │
                                                  ▼
                    ┌──────────────────────────────────────────────┐
                    │ detector/decision.py  (最终裁决)              │
                    │                                              │
                    │  输入: 7 个候选评分                            │
                    │    GBK: 0.82, BIG5: 0.42, UTF8: 0.35, ...   │
                    │                                              │
                    │  处理:                                       │
                    │    softmax 归一化                             │
                    │    → 内容判别器                              │
                    │       CJK/Bopomofo/假名 歧义消解              │
                    │                                              │
                    │  输出: top_candidates + 置信度                │
                    │                                              │
                    │  依赖: encoding.py                           │
                    │        text_analyzer.py                      │
                    └──────────────────┬───────────────────────────┘
                                       │
                                       ▼
                     DetectionResult
                     { encoding:"GBK", std_name:"gbk",
                       is_pure_ascii:false, trials:[...] }
                                       │
                                       ▼
                     ┌─────────────────────────────────────────────┐
                     │ ui/tabs.py 显示结果到界面                    │
                     └─────────────────────────────────────────────┘
```

### 检测流程涉及文件

| 步骤 | 文件 | 职责 |
|---|---|---|
| 用户操作入口 | `ui/tabs.py` | 弹文件选择框、调服务、更新界面 |
| 检测门面 | `services/detector_service.py` | 组合读取+检测+结果整理，返回 `DetectionResult` |
| 检测编排 | `detector/pipeline.py` | 组织 anchors → agents → decision |
| 硬规则 | `detector/anchors.py` | BOM / 纯 ASCII 短路 / UTF-16 结构判别 |
| 编码评分 | `detector/agents.py` | 7 个代理各自对 bytes 打分 |
| 最终裁决 | `detector/decision.py` | softmax + 内容消歧，确定编码 |
| （被依赖） | `encoding.py` | 编码注册表，检测顺序配置 |
| （被依赖） | `text_analyzer.py` | char_category / script_score |
| （被依赖） | `byte_validator.py` | GBK/Big5/SJIS 字节合法性评分 |
| （被依赖） | `character_token.py` | CharacterToken dataclass |

---

## 二、编码转换流程（UTF-8 → GBK）

用户选择源文件、目标编码 GBK，点击"执行转换"。

```
用户点击"执行转换"
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│ ui/tabs.py  (EncodingConverterTab._do_convert)                │
│  获取源/目标编码、策略，调服务                                  │
│  不知道 encode/decode 具体怎么实现                              │
└────────────────────────────────┬─────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│ services/converter_service.py  (转换总管)                     │
│                              │                                │
│  1. 读取 file_to_tokens() → CharacterToken[]                 │
│  2. 兼容性检查 compatibility_scan()                           │
│  3. 执行转换 convert_file()                                  │
│  4. 返回 ConversionResult                                    │
└──────────────┬──────────────────────────────┬────────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│ compatibility.py  (转换前检查) │  │ encoding_converter.py (真正转换)│
│                              │  │                              │
│  输入: CharacterToken[]      │  │  Converter.convert_tokens()  │
│        target_encoding="GBK" │  │                              │
│                              │  │  遍历每个 token:              │
│  对每个字符:                  │  │    char.encode("gbk")        │
│    char.encode("gbk")        │  │    → bytes                  │
│    成功 → compatible++       │  │                              │
│    失败 → problems[]         │  │  失败时:                     │
│                              │  │    replace: "?".encode()     │
│  返回 CompatibilityReport    │  │    strict: 抛出 ValueError   │
│    { rate, compatible,       │  │                              │
│      problem_count, problems }│ │  依赖: encoding.py           │
│                              │  │        compatibility.py     │
│  依赖: encoding.py           │  │                              │
│        character_token.py   │  └──────────────┬───────────────┘
└──────────────────────────────┘                 │
                                                 ▼
                    ┌──────────────────────────────────────────────┐
                    │ verifier.py  (转换后验证)                    │
                    │                                              │
                    │  ConversionVerifier.verify_roundtrip()       │
                    │                                              │
                    │  1. 读取输出文件 bytes                        │
                    │  2. raw.decode("gbk") → recovered_text       │
                    │  3. 逐字符比对：                              │
                    │      原 token.char == recovered_char?         │
                    │                                              │
                    │  返回 ConversionVerdict                      │
                    │    { all_match, match_count, mismatch_count }│
                    │                                              │
                    │  依赖: encoding.py                           │
                    │        display_utils.py                     │
                    └──────────────────┬───────────────────────────┘
                                       │
                                       ▼
                     ConversionResult
                     { path, tokens, total_chars,
                       verified, reversible, all_match }
                                       │
                                       ▼
                     ┌─────────────────────────────────────────────┐
                     │ ui/tabs.py 显示结果 + 提示框                 │
                     └─────────────────────────────────────────────┘
```

### 转换流程涉及文件

| 步骤 | 文件 | 职责 |
|---|---|---|
| 用户操作入口 | `ui/tabs.py` | 按钮响应、参数获取、结果展示 |
| 转换总管 | `services/converter_service.py` | 编排兼容检查→转换→验证 |
| 兼容检查 | `compatibility.py` | 转换前预览哪些字符不可编码 |
| 编码转换 | `encoding_converter.py` | 逐字符 encode 输出 bytes + 写文件 |
| 转换验证 | `verifier.py` | 标准库独立解码比对，验证无损 |
| （被依赖） | `encoding.py` | 编码映射表 |
| （被依赖） | `character_token.py` | CharacterToken |
| （被依赖） | `converter_utils.py` | token_target_display |
| （被依赖） | `display_utils.py` | bytes_to_hex, codepoint_display |

---

## 三、字符 HEX 查看流程（输入"中" → 看到各编码字节）

用户在查看器输入"中"，系统展示"UTF-8: E4 B8 AD / GBK: D6 D0 / Big5: A4 A4"。

```
用户粘贴文本 / 打开文件
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│ ui/tabs.py  (EncodingViewerTab._analyze / _open_file)        │
│  获取 tokens → 调 EncodingViewer → 填表格                     │
└────────────────────────────────┬─────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│ encoding_viewer.py  (EncodingViewer)                          │
│                              │                                │
│  analyze_tokens(tokens)      │                                │
│    → analyze_token(token)    │                                │
│      → analyze_character(char, source_bytes)                  │
│                              │                                │
│  对每个字符:                  │                                │
│    遍历 ALL_ENCODINGS:       │                                │
│      char.encode(std_name)   │                                │
│      → bytes_to_hex(bytes)   │                                │
│      成功 → "E4 B8 AD"       │                                │
│      失败 → "N/A"            │                                │
│                              │                                │
│  get_statistics(results)     │                                │
│    → 各编码支持率统计         │                                │
│                              │                                │
│  依赖: encoding.py           │                                │
│        display_utils.py     │                                │
│        character_token.py   │                                │
└────────────────────────────────┬─────────────────────────────┘
                                 │
                                 ▼
                     ┌───────────────────────────────────────────┐
                     │ ui/tables.py  (ColoredTable.display_data) │
                     │  逐行绘制 Canvas 表格显示                   │
                     │  红底 "N/A"、灰底编码色、字体对齐           │
                     │                                            │
                     │  依赖: encoding.py (颜色)                  │
                     │        encoding_viewer.py (列定义)         │
                     └───────────────────────────────────────────┘
```

---

## 四、功能 ↔ 文件对应表

| 功能 | 主要文件 |
|---|---|
| 打开文件、按钮交互 | `ui/tabs.py` |
| 编码检测流水线 | `detector/anchors.py`, `agents.py`, `decision.py`, `pipeline.py` |
| 检测业务门面 | `services/detector_service.py` |
| 字符 Token | `character_token.py` |
| 编码注册、颜色 | `encoding.py` |
| 编码转换 | `encoding_converter.py` |
| 转换业务门面 | `services/converter_service.py` |
| 兼容性检查 | `compatibility.py` |
| 转换验证 | `verifier.py` |
| 字符 HEX 查看 | `encoding_viewer.py` |
| 字节校验评分 | `byte_validator.py` |
| 文本分析 | `text_analyzer.py` |
| 解码 | `decode_utils.py` |
| 格式工具 | `display_utils.py` |
| Token 显示格式化 | `converter_utils.py` |
| Canvas 表格 | `ui/tables.py` |
| 图例 / 按钮工厂 | `ui/widgets.py` |
| 主窗口 | `ui/app.py` |

---

## 五、所以文件很多，但一次操作不会经过全部

18 个 .py 文件，但每条路径只走其中一部分：

**检测 GBK 文件：** `tabs.py` → `detector_service.py` → `pipeline.py` → `agents.py` → `decision.py` → `encoding.py`

**转换 UTF-8 → GBK：** `tabs.py` → `converter_service.py` → `compatibility.py` → `encoding_converter.py` → `verifier.py` → `encoding.py`

**查看字符 HEX：** `tabs.py` → `encoding_viewer.py` → `display_utils.py` → `tables.py`

重构前一个 `file_detector.py` + `gui.py` 揉在一起，反而看不清每次操作经过了什么。现在每个文件职责单一，路径反而是明确的。

---

## 文件结构

```
src/
├── main.py                    程序入口
├── gui.py                     ← ui/app.py:MainWindow（向后兼容存根）
├── file_detector.py           ← detector/*（向后兼容存根）
│
├── detector/                  检测引擎子包
│   ├── anchors.py             BOM / 纯 ASCII / UTF-16 结构锚点
│   ├── agents.py              7 个编码检测代理评分
│   ├── decision.py            softmax + 内容判别器
│   └── pipeline.py            FileEncodingDetector 管线
│
├── services/                  业务门面层（GUI 唯一入口）
│   ├── result.py              DetectionResult / ConversionResult / CompatibilitySummary
│   ├── detector_service.py    检测服务
│   └── converter_service.py   转换服务
│
├── ui/                        UI 子包
│   ├── app.py                 MainWindow
│   ├── tabs.py                EncodingViewerTab / EncodingConverterTab
│   ├── tables.py              ColoredTable / ConversionResultTable
│   └── widgets.py             ColorLegend / 按钮 / 分隔线工厂
│
├── encoding.py                编码注册中心（唯一数据源）
├── display_utils.py           bytes_to_hex / codepoint_display
├── character_token.py         CharacterToken dataclass
├── encoding_viewer.py         EncodingViewer 逐字符编码分析
├── encoding_converter.py      Converter 编码转换逻辑
├── converter_utils.py         token_target_display
├── compatibility.py           CompatibilityReport + 兼容扫描
├── verifier.py                ConversionVerifier 往返验证
├── byte_validator.py          GBK/Big5/SJIS 字节校验评分
├── decode_utils.py            strict_decode
├── text_analyzer.py           char_category / text_script_score
│
├── logs/
└── output/converted/
```

## 分层依赖

```
        UI (ui/app.py → tabs.py → tables.py → widgets.py)
                         ↓
               Services (detector_service, converter_service)
                    ↙           ↘
        Detector (pipeline)    Converter/Viewer/Verifier
               ↙                ↙    ↘
       Core (encoding, display_utils, character_token, byte_validator, text_analyzer, ...)
```
