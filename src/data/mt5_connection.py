"""
mt5_connection.py
وظيفته: نقطة اتصال واحدة بـ MT5، مع إعادة محاولة لو الاتصال تأخر.
"""
import time

import MetaTrader5 as mt5

from src.utils.logger import get_logger

logger = get_logger("mt5_connection")


def connect_mt5(retries: int = 3, wait_seconds: float = 3.0, timeout_ms: int = 20000) -> bool:
    last_error = None
    for attempt in range(1, retries + 1):
        if mt5.initialize(timeout=timeout_ms):
            return True
        last_error = mt5.last_error()  # نحفظ الخطأ قبل shutdown لأنه بيمسحه
        logger.warning("محاولة الاتصال %d/%d فشلت: %s", attempt, retries, last_error)
        mt5.shutdown()
        time.sleep(wait_seconds)
    logger.error("فشل الاتصال بعد %d محاولات. آخر خطأ: %s", retries, last_error)
    return False