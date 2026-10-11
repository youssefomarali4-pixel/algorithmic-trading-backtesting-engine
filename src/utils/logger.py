"""
logger.py
وظيفته: تسجيل أحداث البوت على الشاشة وفي ملف logs/bot.log.
الملف بيتقسم تلقائياً لما يكبر (2MB) ويحتفظ بآخر 5 نسخ.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT_DIR / "logs"

def get_logger(name: str = "trading_bot") -> logging.Logger:
    logger = logging.getLogger(name)
    # لو الـ logger اتجهز قبل كده، نرجعه زي ما هو (عشان الرسائل متتكررش)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    LOG_DIR.mkdir(exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        LOG_DIR / "bot.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False
    return logger