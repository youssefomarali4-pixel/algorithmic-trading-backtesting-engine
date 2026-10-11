import pandas as pd
import pytest

from src.strategies.ema_crossover import generate_signals


def make_df():
    # سعر ينزل 30 شمعة ثم يطلع 40 شمعة: لازم يحصل تقاطع شراء
    closes = list(range(100, 70, -1)) + list(range(70, 110))
    return pd.DataFrame({
        "open": closes,
        "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes],
        "close": closes,
    })


def test_buy_signal_after_reversal():
    out = generate_signals(make_df(), fast=3, slow=8, atr_period=5)
    assert (out["signal"] == 1).any()


def test_no_signals_during_warmup():
    out = generate_signals(make_df(), fast=3, slow=8, atr_period=5)
    assert (out["signal"].iloc[:8] == 0).all()


def test_missing_columns_raises():
    with pytest.raises(ValueError):
        generate_signals(pd.DataFrame({"close": [1, 2, 3]}), fast=2, slow=3)