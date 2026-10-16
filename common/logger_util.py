"""日志工具：同时输出到控制台和文件"""
import os
import logging
from logging.handlers import RotatingFileHandler

# 日志目录（项目根目录下）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(ROOT, "log")
os.makedirs(LOG_DIR, exist_ok=True)


def get_logger(name: str = "ruoyi-test") -> logging.Logger:
    logger = logging.getLogger(name)

    # 防止重复添加 handler
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    # 文件（单文件最大 10MB，保留 5 个备份）
    fh = RotatingFileHandler(
        os.path.join(LOG_DIR, "test.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


log = get_logger()

if __name__ == "__main__":
    log.info("日志工具测试")
    log.warning("这是一条警告")
