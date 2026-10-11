import pandas as pd
import pytest

from src.backtest.engine import run_backtest
from src.backtest.metrics import summarize
from src.risk.risk_manager import SymbolSpec
from src.utils.config_loader import RiskConfig

GOLD = SymbolSpec(
    tick_size=0.01, value_per_unit=100.0,
    volume_min=0.01, volume_max=100.0, volume_step=0.01, digits=2,
)
RISK = RiskConfig(
    risk_per_trade_percent=1.0, max_daily_loss_percent=3.0,
    sl_atr_multiplier=1.5, rr_ratio=2.0,
)


def make_df(rows):
    # كل صف: (open, high, low, close, atr, signal)
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close", "atr", "signal"])
    df["spread"] = 0
    return df


def test_tp_hit_and_entry_on_next_open():
    df = make_df([
        (1990, 1991, 1989, 1990, 10, 1),   # إشارة شراء على الإغلاق
        (2000, 2001, 1999, 2000, 10, 0),   # دخول على فتح الشمعة دي: 2000
        (2005, 2031, 2004, 2030, 10, 0),   # الـ TP (2030) اتلمس
    ])
    result = run_backtest(df, RISK, GOLD, 10000)
    assert len(result.trades) == 1
    t = result.trades[0]
    assert t.entry == 2000.0
    assert t.reason == "tp"
    assert t.pnl == pytest.approx(180.0)   # 30 × 0.06 لوت × 100


def test_sl_wins_when_both_touched_in_same_candle():
    df = make_df([
        (1990, 1991, 1989, 1990, 10, 1),
        (2000, 2001, 1999, 2000, 10, 0),
        (2000, 2031, 1984, 2000, 10, 0),   # الـ SL (1985) والـ TP (2030) الاتنين اتلمسوا
    ])
    result = run_backtest(df, RISK, GOLD, 10000)
    t = result.trades[0]
    assert t.reason == "sl"
    assert t.pnl == pytest.approx(-90.0)   # 15 × 0.06 لوت × 100


def test_no_signal_no_trades():
    df = make_df([(2000, 2001, 1999, 2000, 10, 0)] * 5)
    result = run_backtest(df, RISK, GOLD, 10000)
    assert result.trades == []
    assert result.final_balance == 10000


def test_summarize_basic():
    s = summarize([100, -50, 100, -50], 1000)
    assert s["trades"] == 4
    assert s["win_rate_pct"] == 50
    assert s["profit_factor"] == pytest.approx(2.0)
    assert s["net_profit"] == 100
    assert s["max_drawdown_pct"] == pytest.approx(4.5454, abs=0.01)
    assert s["max_losing_streak"] == 1