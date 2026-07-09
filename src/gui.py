"""
向后兼容的重新导出桩模块。

所有 UI 类已迁移至 src/ui/ 子包。
本模块仅用于保证旧导入路径（from gui import MainWindow）仍然可用。
"""

from ui.app import MainWindow
