"""
engine.py
محرك باكتيست بسيط. قواعد المحاكاة (عشان النتايج ماتبقاش متفائلة):

1. الإشارة بتتحسب على إغلاق شمعة، والدخول على *فتح* الشمعة اللي بعدها.
2. الشراء بيدخل على سعر Ask (= Open + spread)، والبيع على Bid (= Open).
   والبيع بيخرج على Ask برضه.
3. صفقة واحدة مفتوحة في المرة، وبنتجاهل الإشارات الجديدة لحد ما تقفل.
4. لو الـ SL والـ TP اتلمسوا في نفس الشمعة، نفترض إن الـ SL هو اللي ضرب (الأسوأ).
5. لو الشمعة فتحت بفجوة (Gap) بعد الـ SL، الخروج بيكون على سعر الفتح مش على الـ SL.
6. العمولة: مبلغ ثابت لكل لوت (ذهاب وإياب).
7. حجم اللوت بيتحسب من الرصيد الحالي (المكسب والخسارة بيأثروا على الصفقة الجاية).
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pandas as pd

from src.risk.risk_manager import SymbolSpec, build_trade_plan
from src.utils.config_loader import RiskConfig

REQUIRED_COLUMNS = {"open", "high", "low", "close", "atr", "signal", "spread"}


@dataclass(frozen=True)
class Trade:
    direction: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry: float
    exit: float
    sl: float
    tp: float
    lots: float
    pnl: float
    reason: str            # "tp" أو "sl" أو "end" (اتقفلت في آخر البيانات)
    balance_after: float


@dataclass(frozen=True)
class BacktestResult:
    trades: List[Trade]
    initial_balance: float
    final_balance: float
    skipped_small: int     # إشارات اتخطت لأن اللوت المحسوب أقل من أصغر لوت


def _check_exit(pos: dict, o: float, h: float, l: float) -> Tuple[Optional[float], Optional[str]]:
    """هل الصفقة المفتوحة ضربت SL أو TP في الشمعة دي؟ بنفحص الـ SL الأول (الأسوأ)."""
    if pos["sign"] == 1:
        # شراء: الخروج على سعر Bid
        if o <= pos["sl"]:
            return o, "sl"
        if l <= pos["sl"]:
            return pos["sl"], "sl"
        if h >= pos["tp"]:
            return pos["tp"], "tp"
    else:
        # بيع: الخروج على سعر Ask = Bid + spread
        sp = pos["spread"]
        if o + sp >= pos["sl"]:
            return o + sp, "sl"
        if h + sp >= pos["sl"]:
            return pos["sl"], "sl"
        if l + sp <= pos["tp"]:
            return pos["tp"], "tp"
    return None, None


def _close_trade(pos, exit_price, reason, exit_time, balance, spec, commission_per_lot) -> Trade:
    pnl = pos["sign"] * (exit_price - pos["entry"]) * pos["lots"] * spec.value_per_unit
    pnl -= commission_per_lot * pos["lots"]
    pnl = round(pnl, 2)
    return Trade(
        direction=pos["direction"],
        entry_time=pos["entry_time"],
        exit_time=exit_time,
        entry=pos["entry"],
        exit=round(exit_price, spec.digits),
        sl=pos["sl"],
        tp=pos["tp"],
        lots=pos["lots"],
        pnl=pnl,
        reason=reason,
        balance_after=round(balance + pnl, 2),
    )


def run_backtest(
    df: pd.DataFrame,
    risk: RiskConfig,
    spec: SymbolSpec,
    initial_balance: float,
    commission_per_lot: float = 0.0,
) -> BacktestResult:
    """df لازم يكون خارج generate_signals ومعاه عمود spread (من MT5)."""
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"أعمدة ناقصة في البيانات: {sorted(missing)}")

    times = df.index
    opens = df["open"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    closes = df["close"].to_numpy(dtype=float)
    atrs = df["atr"].to_numpy(dtype=float)
    signals = df["signal"].to_numpy()
    # السبريد في MT5 بالـ points، وبنفترض إن الـ point = tick_size
    spreads = df["spread"].to_numpy(dtype=float) * spec.tick_size

    balance = float(initial_balance)
    trades: List[Trade] = []
    skipped = 0
    pos: Optional[dict] = None

    for i in range(1, len(df)):
        # 1) دخول: مفيش صفقة مفتوحة وفيه إشارة على إغلاق الشمعة اللي فاتت
        if pos is None and signals[i - 1] != 0:
            direction = "buy" if signals[i - 1] == 1 else "sell"
            sp = spreads[i]
            entry = opens[i] + sp if direction == "buy" else opens[i]
            plan = build_trade_plan(direction, entry, atrs[i - 1], balance, risk, spec)
            if plan is None:
                skipped += 1
            else:
                pos = {
                    "direction": direction,
                    "sign": 1 if direction == "buy" else -1,
                    "entry": plan.entry,
                    "sl": plan.sl,
                    "tp": plan.tp,
                    "lots": plan.lots,
                    "spread": sp,
                    "entry_time": times[i],
                }

        # 2) خروج: بنفحص الصفقة المفتوحة (شاملة شمعة الدخول نفسها)
        if pos is not None:
            exit_price, reason = _check_exit(pos, opens[i], highs[i], lows[i])
            if exit_price is not None:
                trade = _close_trade(pos, exit_price, reason, times[i], balance, spec, commission_per_lot)
                trades.append(trade)
                balance = trade.balance_after
                pos = None
                if balance <= 0:
                    break

    # صفقة لسه مفتوحة في آخر البيانات: نقفلها على آخر إغلاق
    if pos is not None:
        last_exit = closes[-1] + (pos["spread"] if pos["sign"] == -1 else 0.0)
        trade = _close_trade(pos, last_exit, "end", times[-1], balance, spec, commission_per_lot)
        trades.append(trade)
        balance = trade.balance_after

    return BacktestResult(
        trades=trades,
        initial_balance=float(initial_balance),
        final_balance=round(balance, 2),
        skipped_small=skipped,
    )