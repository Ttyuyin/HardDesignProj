"""
共享 UI 组件 —— ColorLegend（编码颜色图例）、分隔线工厂函数、按钮工厂函数。
"""

import tkinter as tk
from tkinter import ttk

from encoding import ENCODING_NAMES, NA_BG, NA_FG, get_bg


def create_horizontal_separator(parent):
    """创建水平 ttk 分隔线。"""
    return ttk.Separator(parent, orient="horizontal")


def create_vertical_separator(parent):
    """创建垂直 ttk 分隔线。"""
    return ttk.Separator(parent, orient="vertical")


def create_button(parent, text, cmd, fg_color="#888"):
    """创建统一样式的扁平按钮。

    Args:
        parent: 父容器。
        text: 按钮文本。
        cmd: 点击回调函数。
        fg_color: 背景色（同时也是 active 色），默认灰色。
    """
    return tk.Button(parent, text=text, command=cmd, font=("Microsoft YaHei", 9),
                     bg=fg_color, fg="white", cursor="hand2",
                     bd=0, padx=10, pady=2, relief="flat",
                     activebackground=fg_color, activeforeground="white")


class ColorLegend(tk.Frame):
    """编码颜色图例组件。

    水平排列一行色块标签，每个色块代表一种编码方案的颜色标识。
    最后附加一个 N/A（灰色）色块，表示"该编码不可用"。
    用于帮助用户理解 ColoredTable 中单元格背景色的含义。
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        # 编码名称缩写映射（过长名称改用简短别名，节省水平空间）
        _short = {"Extended ASCII": "扩展ASCII", "Shift-JIS": "SJIS",
                  "UTF-16 LE": "UTF16LE", "UTF-16 BE": "UTF16BE"}
        for name in ENCODING_NAMES:
            bg = get_bg(name)
            label = _short.get(name, name)
            swatch = tk.Frame(self, bg=bg, bd=0, padx=4, pady=1)
            swatch.pack(side="left", padx=2, pady=1)
            tk.Label(swatch, text=f" {label} ", font=("Microsoft YaHei", 8, "bold"),
                     bg=bg, fg="#000").pack()
        # N/A 色块（灰色）—— 表示字符无法用该编码表示
        swatch = tk.Frame(self, bg=NA_BG, bd=0, padx=4, pady=1)
        swatch.pack(side="left", padx=2, pady=1)
        tk.Label(swatch, text=" N/A ", font=("Microsoft YaHei", 8, "bold"),
                 bg=NA_BG, fg=NA_FG).pack()
