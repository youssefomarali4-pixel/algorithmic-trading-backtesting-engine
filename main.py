import MetaTrader5 as mt5

from src.data.data_fetcher import fetch_candles
from src.data.mt5_connection import connect_mt5
from src.utils.config_loader import load_settings
from src.utils.logger import get_logger


def main():
    logger = get_logger()
    settings = load_settings()

    logger.info("جاري الاتصال بـ MetaTrader 5...")
    if not connect_mt5():
        logger.error("فشل الاتصال بـ MT5: %s", mt5.last_error())
        return
    logger.info("تم الاتصال بـ MT5 بنجاح.")

    try:
        df = fetch_candles(
            symbol=settings.mt5.symbol,
            timeframe_str=settings.mt5.timeframe,
            num_bars=settings.mt5.history_bars,
        )
        if df is not None:
            logger.info("أحدث 5 شموع مقفولة:\n%s", df.tail())
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()