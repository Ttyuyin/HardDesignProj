"""
字符编码显示与转换系统
课程设计入口文件
运行方式：python main.py
"""

# Windows 高 DPI 感知 —— 必须在任何 GUI 初始化前设置
import ctypes as _ctypes
try:
    _ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except Exception:
    try:
        _ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import sys
import os
import logging

# 确保能导入同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import MainWindow


def setup_logging():
    """配置日志：同时输出到文件和终端"""
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
    log_file = setup_logging()
    logging.info("=" * 50)
    logging.info("Character encoding display & conversion system started")
    logging.info("Log file: %s", log_file)
    logging.info("=" * 50)

    app = MainWindow()
    app.run()

    logging.info("System exited normally")


if __name__ == "__main__":
    main()
