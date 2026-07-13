# HardDesignProj — 项目最终结构

```
HardDesignProj/
├── src/                          # 核心源码
│   ├── main.py                   # 程序入口，启动 TUI 界面
│   ├── encoding.py               # 编码注册中心（9 种编码）
│   ├── detector/                 # 编码检测模块
│   │   ├── agents.py             # 多代理检测流水线
│   │   ├── anchors.py            # BOM / ASCII 锚点检测
│   │   ├── byte_validator.py     # GBK/Big5/Shift-JIS 字节校验
│   │   ├── decision.py           # softmax 置信度决策
│   │   ├── decode_utils.py       # 解码工具
│   │   ├── pipeline.py           # 检测主流水线
│   │   └── text_analyzer.py      # 字符分类与文本分析
│   ├── converter/                # 编码转换模块
│   │   ├── converter.py          # 编码转换引擎
│   │   ├── converter_utils.py    # 转换工具
│   │   ├── compatibility.py      # 编码兼容性检测
│   │   └── verifier.py           # 转换验证（往返测试）
│   ├── services/                 # 服务层
│   │   ├── detector_service.py   # 检测服务
│   │   ├── converter_service.py  # 转换服务
│   │   └── result.py             # 检测结果模型
│   ├── viewer/                   # 编码查看器
│   │   └── viewer.py             # 字符编码信息展示
│   ├── ui/                       # 用户界面（Textual TUI）
│   │   ├── app.py                # Application 主应用
│   │   ├── tabs.py               # 标签页布局
│   │   ├── tables.py             # 数据表格
│   │   └── widgets.py            # 自定义组件
│   ├── shared/                   # 共享工具
│   │   ├── character_token.py    # 字符 token 模型
│   │   └── display_utils.py      # 显示工具
│   ├── logs/                     # 运行时日志（运行后生成）
│   └── output/                   # 转换输出目录
├── demo_chars/                   # 测试样本数据集（15 个样本）
│   ├── 01_ascii.txt              # ASCII 纯英文
│   ├── 02_utf8_chinese.txt       # UTF-8 中文
│   ├── 03_utf16le.txt            # UTF-16 LE（含 BOM）
│   ├── 04_utf16be.txt            # UTF-16 BE（含 BOM）
│   ├── 05_gbk_chinese.txt        # GBK 中文
│   ├── 06_big5_traditional.txt   # Big5 繁体中文
│   ├── 07_shiftjis_japanese.txt  # Shift-JIS 日文
│   ├── french_chars.txt          # 法文（Latin-1 扩展）
│   ├── korean_chars.txt          # 韩文（UTF-8）
│   ├── gbk_短.txt / gbk_长.txt   # GBK 短/长文本
│   ├── DEMO_DATASET_VERIFY.txt   # 数据集校验说明
│   └── README.txt                # 样本文件说明
├── tests/                        # 测试脚本
│   ├── test_detector.py          # 编码检测测试（15 样本，86.67%）
│   ├── test_converter.py         # 编码转换测试（135 对，96.3%）
│   ├── test_conversion_matrix.py # 转换矩阵测试（4 文本 × 5 编码）
│   ├── test_functional.py        # 单元功能测试（44 项，100%）
│   └── test_software_functional.py # 软件功能测试（8 项，100%）
├── docs/test_reports/            # 最终测试报告
│   ├── encoding_detection_report.md   # 编码检测报告
│   ├── conversion_report.md           # 编码转换报告
│   ├── software_test_report.md        # 软件测试报告
│   └── FINAL_TEST_SUMMARY.md          # 测试总表
├── output/                       # 输出目录（运行时）
├── .gitignore                    # Git 忽略规则
├── requirements.txt              # 依赖说明
├── FINAL_STRUCTURE.md            # 本文件
└── README.md                     # 项目说明文档
```

## 启动方式
```
python src/main.py
```

## 测试方式
```powershell
python tests/test_detector.py
python tests/test_converter.py
python tests/test_conversion_matrix.py
python tests/test_functional.py
python tests/test_software_functional.py
```

## 支持编码（共 9 种）
| 编码 | 标准名 | 类别 | 说明 |
|------|--------|------|------|
| UTF-8 | utf_8 | Unicode | 通用编码，含 BOM 检测 |
| UTF-16 LE | utf_16_le | Unicode | 含 BOM 检测 |
| UTF-16 BE | utf_16_be | Unicode | 含 BOM 检测 |
| UTF-16 | utf_16 | Unicode | BOM 自动识别 |
| ASCII | ascii | 单字节 | 纯英文 |
| GBK | gbk | 中文字符集 | GB2312 超集 |
| Big5 | big5 | 繁体中文字符集 |  |
| Shift-JIS | shift_jis | 日文字符集 |  |
| Extended ASCII | latin_1 | 单字节 | Latin-1（ISO 8859-1） |
