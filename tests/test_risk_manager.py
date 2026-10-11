import pytest

from src.risk.risk_manager import (
    SymbolSpec,
    build_trade_plan,
    calculate_lot_size,
    loss_per_lot,
)
from src.utils.config_loader import RiskConfig

# الذهب: عقد 100 أونصة، يعني حركة 1.00 في السعر = 100$ لكل لوت
GOLD = SymbolSpec(
    tick_size=0.01, value_per_unit=100.0,
    volume_min=0.01, volume_max=100.0, volume_step=0.01, digits=2,
)
RISK = RiskConfig(
    risk_per_trade_percent=1.0, max_daily_loss_percent=3.0,
    sl_atr_multiplier=1.5, rr_ratio=2.0,
)


def test_lot_size_rounds_down():
    assert calculate_lot_size(10000, 1.0, 15.0, GOLD) == 0.06


def test_too_small_trade_is_skipped():
    assert calculate_lot_size(100, 1.0, 15.0, GOLD) == 0.0


def test_buy_plan_levels():
    plan = build_trade_plan("buy", 2000.0, 10.0, 10000, RISK, GOLD)
    assert plan.sl == 1985.0
    assert plan.tp == 2030.0
    assert plan.lots == 0.06
    assert plan.risk_amount == 90.0


def test_sell_plan_levels():
    plan = build_trade_plan("sell", 2000.0, 10.0, 10000, RISK, GOLD)
    assert plan.sl == 2015.0
    assert plan.tp == 1970.0


def test_loss_per_lot_matches_mt5_measurement():
    # MT5 نفسه رجّع 2479$ لحركة 24.79 على لوت واحد
    assert loss_per_lot(24.79, GOLD) == pytest.approx(2479.0)


def test_realistic_gold_lot_size():
    # رصيد 100 ألف، مخاطرة 1% = 1000$، والـ SL مسافته 24.79
    assert calculate_lot_size(100000, 1.0, 24.79, GOLD) == 0.40