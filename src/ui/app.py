"""
MainWindow — application root.
"""

import tkinter as tk
from tkinter import ttk

from ui.tabs import EncodingViewerTab, EncodingConverterTab


class MainWindow:
    BASE_TITLE = "字符编码显示与转换系统 v1.0"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(self.BASE_TITLE)
        self.root.geometry("1200x720")
        self.root.minsize(900, 500)

        style = ttk.Style()
        style.theme_use("vista")
        style.configure("TNotebook", tabmargins=0)
        style.configure("TNotebook.Tab", padding=[14, 4])
        style.map("TNotebook.Tab",
                  background=[("selected", "#FFFFFF")],
                  lightcolor=[("selected", "#2E7D32")])

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        self.viewer_tab = EncodingViewerTab(self.notebook)
        self.notebook.add(self.viewer_tab, text="编码查看器")

        self.converter_tab = EncodingConverterTab(self.notebook)
        self.notebook.add(self.converter_tab, text="编码转换器")

    def _on_tab_change(self, event=None):
        tab_name = self.notebook.tab(self.notebook.select(), "text")
        self.root.title(f"{self.BASE_TITLE}  —  [{tab_name}]")

    def run(self):
        self._on_tab_change()
        self.root.mainloop()
