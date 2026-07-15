"""共享 UI 组件 —— ColorLegend、分隔线工厂函数、按钮工厂函数"""

import tkinter as tk
from tkinter import ttk

from encoding import ENCODING_NAMES, NA_BG, NA_FG, get_bg


def create_horizontal_separator(parent):
    """创建水平分隔线"""
    return ttk.Separator(parent, orient="horizontal")


def create_vertical_separator(parent):
    """创建垂直分隔线"""
    return ttk.Separator(parent, orient="vertical")


def create_button(parent, text, cmd, fg_color="#888"):
    """创建统一样式的按钮"""
    return tk.Button(parent, text=text, command=cmd, font=("Microsoft YaHei", 9),
                     bg=fg_color, fg="white", cursor="hand2",
                     bd=0, padx=10, pady=2, relief="flat",
                     activebackground=fg_color, activeforeground="white")


class ColorLegend(tk.Frame):
    """编码颜色图例组件"""

    def __init__(self, parent, **kwargs):
        """初始化图例，展示每种编码的颜色标识"""
        super().__init__(parent, **kwargs)
        _short = {"Extended ASCII": "扩展ASCII", "Shift-JIS": "SJIS",
                  "UTF-16 LE": "UTF16LE", "UTF-16 BE": "UTF16BE"}
        for name in ENCODING_NAMES:
            bg = get_bg(name)
            label = _short.get(name, name)
            swatch = tk.Frame(self, bg=bg, bd=0, padx=4, pady=1)
            swatch.pack(side="left", padx=2, pady=1)
            tk.Label(swatch, text=f" {label} ", font=("Microsoft YaHei", 8, "bold"),
                     bg=bg, fg="#000").pack()
        swatch = tk.Frame(self, bg=NA_BG, bd=0, padx=4, pady=1)
        swatch.pack(side="left", padx=2, pady=1)
        tk.Label(swatch, text=" N/A ", font=("Microsoft YaHei", 8, "bold"),
                 bg=NA_BG, fg=NA_FG).pack()
