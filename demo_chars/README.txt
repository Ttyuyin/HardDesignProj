================================================================================
Demo Dataset — Character Encoding Detection & Conversion
================================================================================
Generated: 2026-07-10
Purpose: Course design defense demo
Encoding method: Python stdlib encode() — all files are real encoded bytes


================================================================================
Directory Structure
================================================================================

  demo_chars/
  ├── 01_ascii.txt
  ├── 02_utf8_chinese.txt
  ├── 03_utf16le.txt
  ├── 04_utf16be.txt
  ├── 05_gbk_chinese.txt
  ├── 06_big5_traditional.txt
  ├── 07_shiftjis_japanese.txt
  ├── conversion_cases/
  │   ├── case1_utf8_to_gbk.txt
  │   ├── case2_big5_to_gbk.txt
  │   ├── case3_shiftjis_to_utf8.txt
  │   └── case4_utf16_to_utf8.txt
  ├── README.txt
  ├── DEMO_DATASET_VERIFY.txt
  └── generate_demo.py


================================================================================
1. 01_ascii.txt
================================================================================

  Real encoding:        ASCII
  Detector expected:    ASCII
  Purpose:              Demonstrate ASCII detection and UTF-8 compatibility
  Conversion note:      ASCII → any encoding is lossless


================================================================================
2. 02_utf8_chinese.txt
================================================================================

  Real encoding:        UTF-8
  Detector expected:    UTF-8
  Purpose:              Demonstrate UTF-8 Chinese + English mixed detection
  Content:              Chinese, English, digits, punctuation


================================================================================
3. 03_utf16le.txt
================================================================================

  Real encoding:        UTF-16 LE (with BOM: FF FE)
  Detector expected:    UTF-16 LE (BOM anchor → deterministic detection)
  Purpose:              Demonstrate UTF-16 LE with BOM detection
  Conversion note:      UTF-16 LE ↔ UTF-8 is lossless


================================================================================
4. 04_utf16be.txt
================================================================================

  Real encoding:        UTF-16 BE (with BOM: FE FF)
  Detector expected:    UTF-16 BE (BOM anchor → deterministic detection)
  Purpose:              Demonstrate UTF-16 BE with BOM detection
  Note:                 Same content as 03_utf16le.txt, different byte order


================================================================================
5. 05_gbk_chinese.txt
================================================================================

  Real encoding:        GBK
  Detector expected:    GBK
  Purpose:              Demonstrate GBK simplified Chinese detection
  Content:              Simplified Chinese characters, digits


================================================================================
6. 06_big5_traditional.txt
================================================================================

  Real encoding:        Big5
  Detector expected:    Big5
  Purpose:              Demonstrate Big5 traditional Chinese detection
  Content:              Traditional Chinese characters, digits
  Conversion note:      Big5 → GBK (simplified) may lose traditional-specific chars


================================================================================
7. 07_shiftjis_japanese.txt
================================================================================

  Real encoding:        Shift-JIS (CP932)
  Detector expected:    Shift-JIS
  Purpose:              Demonstrate Shift-JIS Japanese detection
  Content:              Hiragana (こんにちは), Katakana (プログラム), Kanji (日本語)
  Note:                 Requires kana content for reliable CJK disambiguation


================================================================================
8. conversion_cases/case1_utf8_to_gbk.txt
================================================================================

  Real encoding:        UTF-8
  Detector expected:    UTF-8
  Purpose:              Demo source for UTF-8 → GBK conversion
  Conversion target:    GBK


================================================================================
9. conversion_cases/case2_big5_to_gbk.txt
================================================================================

  Real encoding:        Big5
  Detector expected:    Big5
  Purpose:              Demo source for Big5 → GBK conversion
  Conversion target:    GBK (simplified Chinese)


================================================================================
10. conversion_cases/case3_shiftjis_to_utf8.txt
================================================================================

  Real encoding:        Shift-JIS
  Detector expected:    Shift-JIS
  Purpose:              Demo source for Shift-JIS → UTF-8 conversion
  Conversion target:    UTF-8 (universal encoding)


================================================================================
11. conversion_cases/case4_utf16_to_utf8.txt
================================================================================

  Real encoding:        UTF-16 LE (with BOM: FF FE)
  Detector expected:    UTF-16 LE
  Purpose:              Demo source for UTF-16 LE → UTF-8 conversion
  Conversion target:    UTF-8


================================================================================
Detection Tips
================================================================================

  - ASCII:   BOM-less, all bytes < 0x80
  - UTF-8:   BOM optional, multi-byte sequences with 0xxxxxxx pattern
  - UTF-16:  BOM strongly preferred for reliable byte-order detection
  - GBK:     Lead byte 0x81-0xFE, trail byte 0x40-0xFE (excluding 0x7F)
  - Big5:    Lead byte 0xA1-0xF9, trail byte 0x40-0x7E or 0xA1-0xFE
  - Shift-JIS: Lead byte 0x81-0x9F or 0xE0-0xFC; half-width kana 0xA1-0xDF


================================================================================
Verification
================================================================================

  All 11 files PASS independent verification (see DEMO_DATASET_VERIFY.txt).
  Each file was verified by:
    1. Reading raw bytes
    2. Decoding with claimed encoding
    3. Re-encoding to confirm byte-exact match
