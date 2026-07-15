"""字符编码显示与转换系统 — 课程设计入口文件"""

import ctypes as _ctypes
try:
    _ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        _ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import MainWindow


def setup_logging():
    """初始化日志系统（文件 + 控制台）"""
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
    """程序入口：启动 GUI 主窗口"""
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
