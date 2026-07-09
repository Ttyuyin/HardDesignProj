"""
Canvas 驱动的高性能表格组件 —— ColoredTable（编码分析表）、ConversionResultTable（转换结果表）及基类。

所有表格均使用 tk.Canvas 进行像素级绘制，避免 ttk.Treeview 的样式限制，
支持独立表头、同步滚动和自定义单元格颜色。
"""

import tkinter as tk
from tkinter import font

from converter_utils import token_target_display
from encoding import ENCODING_NAMES, NA_BG, NA_FG, get_bg
from encoding_viewer import EncodingViewer


# ---------------------------------------------------------------------------
# _CanvasTableBase —— 像素级 Canvas 表格基类
# ---------------------------------------------------------------------------
class _CanvasTableBase(tk.Frame):
    """基于 tk.Canvas 的像素级精确表格基类。

    核心设计：
    - 使用**双层 Canvas**：header_canvas（表头，固定不随垂直滚动移动）
      和 data_canvas（数据区，支持垂直 + 水平滚动）。
    - 水平滚动时 header_canvas 与 data_canvas 同步。
    - 列宽度以 "字符数 × 等宽字体像素宽度" 为单位，确保文字对齐精确。
    - 子类只需实现 _draw_data_row 和列配置（COLUMNS / COL_CONFIG）。
    """
    COLUMNS = []         # 列名列表（顺序定义）
    COL_CONFIG = {}      # 列名 → (字符宽度, 对齐方式)  例："Char": (8, "left")

    ROW_HEIGHT = 26       # 每行数据高度（像素）
    HEADER_HEIGHT = 28    # 表头高度（像素）
    CELL_PAD = 5          # 单元格内边距（像素）
    _CHAR_GAP = 2         # 列之间额外间距（字符宽度倍数）

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._setup_fonts()
        self._setup_ui()

    # ── 字体初始化 & 列宽像素计算 ──────────────────────────────────────

    def _setup_fonts(self):
        """初始化三种字体，并计算每列在像素坐标系中的起始 x 坐标和宽度。

        _col_x[j] / _col_w[j] 分别对应 COLUMNS 中第 j 列的 x 起点与宽度。
        _char_w 以 Consolas '0' 为基准，确保等宽对齐。
        """
        self._font_mono = font.Font(family="Consolas", size=11)
        self._font_header = font.Font(family="Microsoft YaHei", size=11, weight="bold")
        self._font_char = font.Font(family="Microsoft YaHei", size=11)
        self._char_w = self._font_mono.measure("0")
        self._gap_px = self._char_w * self._CHAR_GAP

        x = 0
        self._col_x = []
        self._col_w = []
        for col in self.COLUMNS:
            self._col_x.append(x)
            w = self.COL_CONFIG[col][0] * self._char_w   # 字符宽度 × 基准像素
            self._col_w.append(w)
            x += w + self._gap_px
        self._total_w = x - self._gap_px                 # 总宽度（去掉尾部多余间距）

    def _setup_ui(self):
        """构建双层 Canvas + 滚动条的 UI 布局。

        行布局：[0] 表头 Canvas（固定高度），[1] 数据 Canvas（可拉伸），[2] 水平滚动条。
        列布局：[0] Canvas，[1] 垂直滚动条。
        """
        # 第 1 行（数据区）可拉伸，第 0 行（表头）固定高度
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── 表头 Canvas（固定，不参与垂直滚动） ──
        self.header_canvas = tk.Canvas(self, bg="#FAFAFA", highlightthickness=0,
                                       height=self.HEADER_HEIGHT)
        self.header_canvas.grid(row=0, column=0, sticky="ew")
        self.header_canvas.grid_propagate(False)

        # ── 数据 Canvas（可滚动，包含垂直 + 水平同步滚动） ──
        self.data_canvas = tk.Canvas(self, bg="#FAFAFA", highlightthickness=0)
        self.vbar = tk.Scrollbar(self, orient="vertical", command=self.data_canvas.yview)
        self.hbar = tk.Scrollbar(self, orient="horizontal", command=self._on_hscroll)
        self.data_canvas.configure(yscrollcommand=self.vbar.set,
                                   xscrollcommand=self.hbar.set)
        self.data_canvas.grid(row=1, column=0, sticky="nsew")
        self.vbar.grid(row=1, column=1, sticky="ns")
        self.hbar.grid(row=2, column=0, sticky="ew")

        # 鼠标滚轮事件：无 Shift → 垂直滚动，有 Shift → 水平滚动
        self.data_canvas.bind("<MouseWheel>", self._on_vscroll_wheel)
        self.data_canvas.bind("<Shift-MouseWheel>", self._on_hscroll_wheel)

    # ── 滚动辅助（垂直 / 水平 / 同步） ─────────────────────────────────

    def _on_vscroll_wheel(self, event):
        """垂直滚轮：仅在 data_canvas 上滚动。"""
        self.data_canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def _on_hscroll_wheel(self, event):
        """水平滚轮（Shift + 滚轮）：两个 Canvas 同步水平滚动。"""
        delta = -1 * (event.delta // 120)
        self.data_canvas.xview_scroll(delta, "units")
        self.header_canvas.xview_scroll(delta, "units")

    def _on_hscroll(self, *args):
        """水平滚动条回调 —— 同步 data_canvas 和 header_canvas。"""
        self.data_canvas.xview(*args)
        self.header_canvas.xview(*args)

    # ── 绘制方法（表头 + 数据行模板） ──────────────────────────────────

    def _draw_header(self):
        """绘制表头：灰色背景矩形 + 每列标题文字（根据 COL_CONFIG 对齐）。"""
        h = self.HEADER_HEIGHT
        self.header_canvas.delete("all")
        self.header_canvas.create_rectangle(0, 0, self._total_w, h,
                                            fill="#D6D6D6", outline="")
        for j, col in enumerate(self.COLUMNS):
            _, align = self.COL_CONFIG[col]
            cx = (self._col_x[j] + self.CELL_PAD) if align == "left" \
                 else (self._col_x[j] + self._col_w[j] - self.CELL_PAD)
            self.header_canvas.create_text(
                cx, h // 2, text=self._header_display(col),
                font=self._font_header,
                anchor="w" if align == "left" else "e", fill="#111111",
            )

    def _draw_data_row(self, y, row_data):
        """绘制一行数据 —— 由子类实现具体绘制逻辑。"""
        raise NotImplementedError

    def display_data(self, items):
        """清空并刷新所有行数据，更新滚动区域边界。"""
        self._draw_header()
        self.data_canvas.delete("all")
        y = 0
        for item in items:
            self._draw_data_row(y, item)
            y += self.ROW_HEIGHT
        total_h = len(items) * self.ROW_HEIGHT
        self.data_canvas.configure(scrollregion=(0, 0, self._total_w, max(total_h, 1)))
        self.header_canvas.configure(scrollregion=(0, 0, self._total_w, 1))

    def clear(self):
        """清空数据区，仅保留表头。"""
        self._draw_header()
        self.data_canvas.delete("all")
        self.data_canvas.configure(scrollregion=(0, 0, self._total_w, 1))


# ---------------------------------------------------------------------------
# ColoredTable —— 编码分析表（查看器标签页右侧表格）
# ---------------------------------------------------------------------------
class ColoredTable(_CanvasTableBase):
    """编码分析表格，在 tk.Canvas 上实现像素级精确对齐。

    列配置说明：
    - Char / Unicode / Raw Bytes：信息列，左对齐。
    - ASCII / Extended ASCII / Shift-JIS / GB2312 / GBK / Big5 / UTF-8 / UTF-16 LE/BE：
      编码可用性列，右对齐显示 "✓" 或 "N/A"。
    - 编码列背景色：N/A → 灰色（不可用），"✓" → 编码对应的特征色。
    """
    COLUMNS = EncodingViewer.COLUMN_ORDER
    COL_CONFIG = {
        "Char":            (8,  "left"),       # 字符本身
        "Unicode":         (14, "left"),       # Unicode 码位（U+XXXX）
        "Raw Bytes":       (14, "left"),       # 原始字节（十六进制）
        "ASCII":           (12, "right"),      # ASCII 编码兼容性
        "Extended ASCII":  (20, "right"),      # 扩展 ASCII（Latin-1）
        "Shift-JIS":       (14, "right"),      # Shift-JIS（日文）
        "GB2312":          (12, "right"),      # GB2312（简体中文）
        "GBK":             (12, "right"),      # GBK（中文扩展）
        "Big5":            (12, "right"),      # Big5（繁体中文）
        "UTF-8":           (12, "right"),      # UTF-8
        "UTF-16 LE":       (14, "right"),      # UTF-16 小端
        "UTF-16 BE":       (14, "right"),      # UTF-16 大端
    }
    _ENC_COLS = set(ENCODING_NAMES)

    _HEADER_LABELS = {
        "Char": "字符",
        "Unicode": "Unicode",
        "Raw Bytes": "原始字节",
    }

    @classmethod
    def _header_display(cls, col):
        """将英文列名映射为中文表头显示。"""
        return cls._HEADER_LABELS.get(col, f"{col} 值")

    def _cell_bg(self, col, val):
        """计算单元格背景色：
        - 编码列 + 值为 N/A → NA_BG（灰色，表示该字符无法用此编码表示）
        - 编码列 + 有值 → 编码对应的特征色（如 GB2312→蓝色系）
        - 其他列 → 白色。
        """
        if col in self._ENC_COLS and val == "N/A":
            return NA_BG
        if col in self._ENC_COLS:
            return get_bg(col)
        return "#FFFFFF"

    def _draw_data_row(self, y, row_data):
        """绘制一行数据：为每列绘制背景矩形 + 文字。

        Char 列使用微软雅黑字体，其余列使用 Consolas 等宽字体。
        N/A 值使用浅色文字（NA_FG），有值使用深色文字。
        """
        h = self.ROW_HEIGHT
        for j, col in enumerate(self.COLUMNS):
            val = str(row_data.get(col, "N/A"))
            _, align = self.COL_CONFIG[col]
            bg = self._cell_bg(col, val)
            is_na = (col in self._ENC_COLS and val == "N/A")
            fnt = self._font_char if col == "Char" else self._font_mono
            cx = (self._col_x[j] + self.CELL_PAD) if align == "left" \
                 else (self._col_x[j] + self._col_w[j] - self.CELL_PAD)
            self.data_canvas.create_rectangle(
                self._col_x[j], y, self._col_x[j] + self._col_w[j], y + h,
                fill=bg, outline="")
            self.data_canvas.create_text(
                cx, y + h // 2, text=val, font=fnt,
                anchor="w" if align == "left" else "e",
                fill=NA_FG if is_na else "#111111")


# ---------------------------------------------------------------------------
# ConversionResultTable —— 转换结果表（转换器标签页）
# ---------------------------------------------------------------------------
class ConversionResultTable(_CanvasTableBase):
    """编码转换结果表格，布局风格与 ColoredTable 保持一致。

    列配置说明：
    - Char / Unicode / Source Encoding / Raw Bytes：源字符信息。
    - Target Encoding：目标编码名称。
    - Converted Bytes：转换后的十六进制字节，背景绿色表示有转换结果。
    """
    COLUMNS = ["Char", "Unicode", "Source Encoding", "Raw Bytes",
               "Target Encoding", "Converted Bytes"]
    COL_CONFIG = {
        "Char":             (8,  "left"),       # 字符
        "Unicode":          (14, "left"),       # Unicode 码位
        "Source Encoding":  (18, "left"),       # 源编码名称
        "Raw Bytes":        (16, "right"),      # 源编码下的原始字节
        "Target Encoding":  (18, "left"),       # 目标编码名称
        "Converted Bytes":  (20, "right"),      # 目标编码下的转换后字节
    }
    _ENC_COLS = {"Source Encoding", "Target Encoding"}

    _HEADER_LABELS = {
        "Char": "字符",
        "Unicode": "Unicode",
        "Raw Bytes": "原始字节",
        "Source Encoding": "源编码",
        "Target Encoding": "目标编码",
        "Converted Bytes": "转换后的字节",
    }

    @classmethod
    def _header_display(cls, col):
        """将英文列名映射为中文表头显示。"""
        return cls._HEADER_LABELS.get(col, col)

    def _setup_ui(self):
        """在基类布局基础上，添加空状态占位标签。"""
        super()._setup_ui()
        self.empty_lbl = tk.Label(self, text="（尚未执行转换）",
                                   fg="#999", bg="#F0F0F0")
        self.empty_lbl.place(relx=0.5, rely=0.5, anchor="center")

    def _get_val(self, token, col):
        """从 CharacterToken 中按列名提取对应的显示值。

        Converted Bytes 列特殊处理：调用 token_target_display 获取格式化后的字节串。
        """
        mapping = {
            "Char": token.char,
            "Unicode": token.unicode_codepoint,
            "Source Encoding": token.source_encoding,
            "Raw Bytes": token.source_bytes_hex,
            "Target Encoding": token.target_encoding,
            "Converted Bytes": token_target_display(token),
        }
        val = mapping.get(col, "")
        return str(val) if val else ""

    def _cell_bg(self, col, val, token):
        """计算单元格背景色：
        - Converted Bytes 列：有目标编码时绿色（#C8E6C9），否则浅灰
        - 编码列（Source / Target）：根据编码名称获取特征色
        - 其他列：白色。
        """
        if col == "Converted Bytes":
            if token.target_encoding:
                return "#C8E6C9"
            return "#F5F5F5"
        if col in self._ENC_COLS and val:
            return get_bg(val)
        return "#FFFFFF"

    def _cell_fg(self, col, val, token):
        """计算单元格文字颜色：
        - Converted Bytes 列：有目标编码时深绿，否则深灰
        - 其他列：默认深色。
        """
        if col == "Converted Bytes":
            if token.target_encoding:
                return "#1B5E20"
            return "#333"
        return "#111111"

    def _draw_data_row(self, y, token):
        """绘制一行转换结果数据。"""
        h = self.ROW_HEIGHT
        for j, col in enumerate(self.COLUMNS):
            val = self._get_val(token, col)
            _, align = self.COL_CONFIG[col]
            bg = self._cell_bg(col, val, token)
            fg = self._cell_fg(col, val, token)
            fnt = self._font_char if col == "Char" else self._font_mono
            cx = (self._col_x[j] + self.CELL_PAD) if align == "left" \
                 else (self._col_x[j] + self._col_w[j] - self.CELL_PAD)
            self.data_canvas.create_rectangle(
                self._col_x[j], y, self._col_x[j] + self._col_w[j], y + h,
                fill=bg, outline="")
            self.data_canvas.create_text(
                cx, y + h // 2, text=val, font=fnt,
                anchor="w" if align == "left" else "e", fill=fg)

    def display_results(self, tokens):
        """显示转换结果：隐藏空状态标签，调用基类 display_data 渲染表格行。"""
        self.empty_lbl.place_forget()
        self.display_data(tokens)

    def clear(self):
        """清空数据，重新显示空状态标签。"""
        self._draw_header()
        self.data_canvas.delete("all")
        self.data_canvas.configure(scrollregion=(0, 0, 0, 0))
        self.empty_lbl.place(relx=0.5, rely=0.5, anchor="center")
