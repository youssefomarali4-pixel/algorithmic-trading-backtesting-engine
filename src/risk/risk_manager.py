"""
risk_manager.py
وظيفته: يحسب حجم اللوت، ووقف الخسارة (SL)، والهدف (TP).

الفكرة: نحدد الأول "أقصى مبلغ مستعدين نخسره" في الصفقة (نسبة من الرصيد)،
وبعدين نحسب اللوت اللي لو السعر وصل لوقف الخسارة، الخسارة تبقى في الحدود دي.

ملحوظة: قيمة الحركة بنقرأها من MT5 نفسه (order_calc_profit) ومش من tick_value،
لأن tick_value طلع غلط عند الوسيط (أصغر 10 مرات من الحقيقي للذهب).
"""
import math
from dataclasses import dataclass
from typing import Optional

from src.utils.config_loader import RiskConfig


@dataclass(frozen=True)
class SymbolSpec:
    """مواصفات الرمز عند الوسيط."""
    tick_size: float        # أصغر حركة للسعر
    value_per_unit: float   # الربح/الخسارة بعملة الحساب لحركة 1.00 في السعر بلوت واحد
    volume_min: float       # أصغر لوت مسموح
    volume_max: float       # أكبر لوت مسموح
    volume_step: float      # خطوة اللوت (مثلاً 0.01)
    digits: int             # عدد الأرقام العشرية في السعر


@dataclass(frozen=True)
class TradePlan:
    direction: str          # "buy" أو "sell"
    entry: float
    sl: float
    tp: float
    lots: float
    risk_amount: float      # الخسارة الفعلية لو ضرب الـ SL
    sl_distance: float


def load_symbol_spec(symbol: str) -> SymbolSpec:
    """يقرأ مواصفات الرمز من MT5 (لازم يكون MT5 متصل)."""
    import MetaTrader5 as mt5

    mt5.symbol_select(symbol, True)
    info = mt5.symbol_info(symbol)
    if info is None:
        raise ValueError(f"الرمز '{symbol}' مش موجود عند الوسيط.")

    tick = mt5.symbol_info_tick(symbol)
    if tick is None or tick.ask <= 0:
        raise ValueError(f"تعذر قراءة السعر الحالي للرمز '{symbol}'.")

    # نسأل MT5: لو لوت شراء واحد اتحرك السعر مسافة "probe"، كام الربح بعملة الحساب؟
    probe = info.trade_tick_size * 1000   # للذهب = 10.00
    profit = mt5.order_calc_profit(
        mt5.ORDER_TYPE_BUY, symbol, 1.0, tick.ask, tick.ask + probe
    )
    if profit is None or profit <= 0:
        raise ValueError(f"تعذر حساب قيمة الحركة من MT5: {mt5.last_error()}")

    return SymbolSpec(
        tick_size=info.trade_tick_size,
        value_per_unit=profit / probe,
        volume_min=info.volume_min,
        volume_max=info.volume_max,
        volume_step=info.volume_step,
        digits=info.digits,
    )


def loss_per_lot(sl_distance: float, spec: SymbolSpec) -> float:
    """الخسارة بالفلوس لو السعر قطع مسافة الـ SL بلوت واحد."""
    return sl_distance * spec.value_per_unit


def calculate_lot_size(
    balance: float, risk_percent: float, sl_distance: float, spec: SymbolSpec
) -> float:
    """
    يرجع حجم اللوت. بنقرّب دايماً لتحت (مش لفوق) عشان المخاطرة ماتزيدش.
    لو الناتج أقل من أصغر لوت مسموح، يرجع 0 (يعني نتخطى الصفقة)،
    لأن رفعه لأصغر لوت معناه مخاطرة أكبر من المسموح.
    """
    risk_amount = balance * risk_percent / 100
    per_lot = loss_per_lot(sl_distance, spec)
    if per_lot <= 0:
        return 0.0

    raw_lots = risk_amount / per_lot
    steps = math.floor(raw_lots / spec.volume_step + 1e-9)
    lots = min(steps * spec.volume_step, spec.volume_max)

    if lots < spec.volume_min:
        return 0.0
    return round(lots, 8)


def build_trade_plan(
    direction: str,
    entry: float,
    atr: float,
    balance: float,
    risk: RiskConfig,
    spec: SymbolSpec,
) -> Optional[TradePlan]:
    """يبني خطة الصفقة كاملة، أو يرجع None لو الصفقة مش مناسبة."""
    if direction not in ("buy", "sell"):
        raise ValueError("direction لازم يكون 'buy' أو 'sell'.")

    # نحوّل لأرقام بايثون العادية (pandas بيرجع np.float64)
    entry, atr, balance = float(entry), float(atr), float(balance)

    sl_distance = atr * risk.sl_atr_multiplier
    if sl_distance <= 0:
        return None

    if direction == "buy":
        sl = entry - sl_distance
        tp = entry + sl_distance * risk.rr_ratio
    else:
        sl = entry + sl_distance
        tp = entry - sl_distance * risk.rr_ratio

    lots = calculate_lot_size(balance, risk.risk_per_trade_percent, sl_distance, spec)
    if lots == 0:
        return None

    return TradePlan(
        direction=direction,
        entry=round(entry, spec.digits),
        sl=round(sl, spec.digits),
        tp=round(tp, spec.digits),
        lots=lots,
        risk_amount=round(lots * loss_per_lot(sl_distance, spec), 2),
        sl_distance=sl_distance,
    )