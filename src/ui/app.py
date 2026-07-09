"""
应用主窗口 —— 字符编码显示与转换系统的入口点。
管理顶层 tk.Tk 实例、样式配置以及两个核心标签页的创建与切换。
"""

import tkinter as tk
from tkinter import ttk

from ui.tabs import EncodingViewerTab, EncodingConverterTab


class MainWindow:
    """应用主窗口，容纳 Notebook 及两个标签页（编码查看器 / 编码转换器）。"""

    BASE_TITLE = "字符编码显示与转换系统 v1.0"

    def __init__(self):
        """初始化根窗口、ttk 样式、Notebook 组件，并添加两个功能标签页。"""
        self.root = tk.Tk()
        self.root.title(self.BASE_TITLE)
        self.root.geometry("1200x720")       # 默认窗口尺寸 1200x720
        self.root.minsize(900, 500)          # 最小窗口尺寸，防止控件被过度压缩

        # -- 样式配置：使用 vista 主题，自定义标签页外观 --
        style = ttk.Style()
        style.theme_use("vista")
        style.configure("TNotebook", tabmargins=0)                 # 取消标签页之间的空隙
        style.configure("TNotebook.Tab", padding=[14, 4])          # 左右 14px，上下 4px
        style.map("TNotebook.Tab",
                  background=[("selected", "#FFFFFF")],             # 选中标签页为白色底
                  lightcolor=[("selected", "#2E7D32")])             # 选中指示条为绿色

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        # -- 创建两个标签页 --
        self.viewer_tab = EncodingViewerTab(self.notebook)
        self.notebook.add(self.viewer_tab, text="编码查看器")

        self.converter_tab = EncodingConverterTab(self.notebook)
        self.notebook.add(self.converter_tab, text="编码转换器")

    def _on_tab_change(self, event=None):
        """标签页切换回调：在窗口标题中追加当前标签页名称。"""
        tab_name = self.notebook.tab(self.notebook.select(), "text")
        self.root.title(f"{self.BASE_TITLE}  —  [{tab_name}]")

    def run(self):
        """启动应用：初始化标题显示，进入 tkinter 主事件循环。"""
        self._on_tab_change()
        self.root.mainloop()
