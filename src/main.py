"""
字符编码显示与转换系统
课程设计入口文件
运行方式：python main.py
"""

# 启用 Windows 高 DPI 感知 —— 必须在任何 GUI 初始化之前设置，否则界面在高 DPI 显示器上会模糊
import ctypes as _ctypes
try:
    # 首选 Per-Monitor DPI Aware（Windows 8.1+），每个监视器独立缩放
    _ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        # 回退到系统级别 DPI 感知（Windows Vista+）
        _ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import sys
import os
import logging

# 确保能导入同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import MainWindow


def setup_logging():
    """配置日志：同时输出到文件和终端。日志目录位于 src/logs/ 下"""
    # 计算日志目录路径：取当前文件（main.py）所在目录下的 logs 子目录
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "encoding.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return log_file


def main():
    """应用程序入口：配置日志 → 初始化主窗口 → 运行事件循环"""
    log_file = setup_logging()
    logging.info("=" * 50)
    logging.info("字符编码显示与转换系统启动")
    logging.info("日志文件: %s", log_file)
    logging.info("=" * 50)

    app = MainWindow()
    app.run()

    logging.info("系统正常退出")


if __name__ == "__main__":
    main()
