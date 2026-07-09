"""
Canvas-based tables — ColoredTable, ConversionResultTable, base class.
"""

import tkinter as tk
from tkinter import font

from converter_utils import token_target_display
from encoding import ENCODING_NAMES, NA_BG, NA_FG, get_bg
from encoding_viewer import EncodingViewer


# ---------------------------------------------------------------------------
# _CanvasTableBase – 像素级 Canvas 表格基类
# ---------------------------------------------------------------------------
class _CanvasTableBase(tk.Frame):
    """Canvas-based table with consistent layout (font, scroll, header)

    使用双层 Canvas：header_canvas 固定不滚动，data_canvas 可垂直滚动。
    水平滚动时两者同步。
    """
    COLUMNS = []
    COL_CONFIG = {}

    ROW_HEIGHT = 26
    HEADER_HEIGHT = 28
    CELL_PAD = 5
    _CHAR_GAP = 2

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._setup_fonts()
        self._setup_ui()

    # ── fonts & column pixel geometry ──────────────────────────────────────

    def _setup_fonts(self):
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
            w = self.COL_CONFIG[col][0] * self._char_w
            self._col_w.append(w)
            x += w + self._gap_px
        self._total_w = x - self._gap_px

    def _setup_ui(self):
        # 第 1 行（数据区）可拉伸，第 0 行（表头）固定高度
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Header canvas (fixed, no vertical scroll) ──
        self.header_canvas = tk.Canvas(self, bg="#FAFAFA", highlightthickness=0,
                                       height=self.HEADER_HEIGHT)
        self.header_canvas.grid(row=0, column=0, sticky="ew")
        self.header_canvas.grid_propagate(False)

        # ── Data canvas (scrollable) ──
        self.data_canvas = tk.Canvas(self, bg="#FAFAFA", highlightthickness=0)
        self.vbar = tk.Scrollbar(self, orient="vertical", command=self.data_canvas.yview)
        self.hbar = tk.Scrollbar(self, orient="horizontal", command=self._on_hscroll)
        self.data_canvas.configure(yscrollcommand=self.vbar.set,
                                   xscrollcommand=self.hbar.set)
        self.data_canvas.grid(row=1, column=0, sticky="nsew")
        self.vbar.grid(row=1, column=1, sticky="ns")
        self.hbar.grid(row=2, column=0, sticky="ew")

        self.data_canvas.bind("<MouseWheel>", self._on_vscroll_wheel)
        self.data_canvas.bind("<Shift-MouseWheel>", self._on_hscroll_wheel)

    # ── scroll helpers ─────────────────────────────────────────────────────

    def _on_vscroll_wheel(self, event):
        self.data_canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def _on_hscroll_wheel(self, event):
        delta = -1 * (event.delta // 120)
        self.data_canvas.xview_scroll(delta, "units")
        self.header_canvas.xview_scroll(delta, "units")

    def _on_hscroll(self, *args):
        """Horizontal scrollbar command — sync both canvases."""
        self.data_canvas.xview(*args)
        self.header_canvas.xview(*args)

    # ── drawing ────────────────────────────────────────────────────────────

    def _draw_header(self):
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
        raise NotImplementedError

    def display_data(self, items):
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
        self._draw_header()
        self.data_canvas.delete("all")
        self.data_canvas.configure(scrollregion=(0, 0, self._total_w, 1))


# ---------------------------------------------------------------------------
# ColoredTable – encoding analysis table (viewer tab)
# ---------------------------------------------------------------------------
class ColoredTable(_CanvasTableBase):
    """Encoding analysis table — pixel-perfect alignment on tk.Canvas"""
    COLUMNS = EncodingViewer.COLUMN_ORDER
    COL_CONFIG = {
        "Char":            (8,  "left"),
        "Unicode":         (14, "left"),
        "Raw Bytes":       (14, "left"),
        "ASCII":           (12, "right"),
        "Extended ASCII":  (20, "right"),
        "Shift-JIS":       (14, "right"),
        "GB2312":          (12, "right"),
        "GBK":             (12, "right"),
        "Big5":            (12, "right"),
        "UTF-8":           (12, "right"),
        "UTF-16 LE":       (14, "right"),
        "UTF-16 BE":       (14, "right"),
    }
    _ENC_COLS = set(ENCODING_NAMES)

    _HEADER_LABELS = {
        "Char": "字符",
        "Unicode": "Unicode",
        "Raw Bytes": "原始字节",
    }

    @classmethod
    def _header_display(cls, col):
        return cls._HEADER_LABELS.get(col, f"{col} 值")

    def _cell_bg(self, col, val):
        if col in self._ENC_COLS and val == "N/A":
            return NA_BG
        if col in self._ENC_COLS:
            return get_bg(col)
        return "#FFFFFF"

    def _draw_data_row(self, y, row_data):
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
# ConversionResultTable – Canvas-based conversion results table
# ---------------------------------------------------------------------------
class ConversionResultTable(_CanvasTableBase):
    """Conversion results table matching ColoredTable layout style"""
    COLUMNS = ["Char", "Unicode", "Source Encoding", "Raw Bytes",
               "Target Encoding", "Converted Bytes"]
    COL_CONFIG = {
        "Char":             (8,  "left"),
        "Unicode":          (14, "left"),
        "Source Encoding":  (18, "left"),
        "Raw Bytes":        (16, "right"),
        "Target Encoding":  (18, "left"),
        "Converted Bytes":  (20, "right"),
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
        return cls._HEADER_LABELS.get(col, col)

    def _setup_ui(self):
        super()._setup_ui()
        self.empty_lbl = tk.Label(self, text="（尚未执行转换）",
                                   fg="#999", bg="#F0F0F0")
        self.empty_lbl.place(relx=0.5, rely=0.5, anchor="center")

    def _get_val(self, token, col):
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
        if col == "Converted Bytes":
            if token.target_encoding:
                return "#C8E6C9"
            return "#F5F5F5"
        if col in self._ENC_COLS and val:
            return get_bg(val)
        return "#FFFFFF"

    def _cell_fg(self, col, val, token):
        if col == "Converted Bytes":
            if token.target_encoding:
                return "#1B5E20"
            return "#333"
        return "#111111"

    def _draw_data_row(self, y, token):
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
        self.empty_lbl.place_forget()
        self.display_data(tokens)

    def clear(self):
        """Clear data content, hide empty label"""
        self._draw_header()
        self.data_canvas.delete("all")
        self.data_canvas.configure(scrollregion=(0, 0, 0, 0))
        self.empty_lbl.place(relx=0.5, rely=0.5, anchor="center")
