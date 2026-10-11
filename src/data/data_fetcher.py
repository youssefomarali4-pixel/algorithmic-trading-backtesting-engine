"""
data_fetcher.py
وظيفته: جلب بيانات الشموع التاريخية من MetaTrader 5 وتحويلها لـ DataFrame.
"""

import MetaTrader5 as mt5
import pandas as pd
from typing import Optional
from src.utils.logger import get_logger

logger = get_logger("data_fetcher")

TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


def fetch_candles(
    symbol: str,
    timeframe_str: str,
    num_bars: int,
    drop_incomplete: bool = True,
) -> Optional[pd.DataFrame]:
    """
    يجلب أحدث num_bars شمعة للرمز على الفريم المحدد.
    drop_incomplete=True يحذف الشمعة الأخيرة لأنها لسه بتتكوّن
    (ولو حسبنا عليها إشارات هتظهر وتختفي).
    """
    if timeframe_str not in TIMEFRAME_MAP:
        logger.error("الفريم '%s' غير مدعوم.", timeframe_str)
        return None

    tf = TIMEFRAME_MAP[timeframe_str]

    if not mt5.symbol_select(symbol, True):
        logger.error("تعذر تفعيل الرمز %s في Market Watch.", symbol)
        return None

    # بنطلب شمعة زيادة لأننا هنحذف الأخيرة
    count = num_bars + 1 if drop_incomplete else num_bars
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is None or len(rates) == 0:
        logger.error("فشل جلب الشموع للرمز %s: %s", symbol, mt5.last_error())
        return None

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("time", inplace=True)

    if drop_incomplete:
        df = df.iloc[:-1]

    logger.info(
        "تم جلب %d شمعة مقفولة للرمز %s على فريم %s بنجاح.",
        len(df), symbol, timeframe_str,
    )
    return df