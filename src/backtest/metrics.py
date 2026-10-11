"""
metrics.py
وظيفته: يحسب إحصائيات الأداء من قائمة أرباح/خسائر الصفقات.
"""
from typing import Dict, List


def summarize(pnls: List[float], initial_balance: float) -> Dict[str, float]:
    n = len(pnls)
    if n == 0:
        return {"trades": 0}

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_profit = sum(wins)
    gross_loss = -sum(losses)
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # أقصى تراجع (Drawdown) على منحنى الرصيد بعد كل صفقة مقفولة
    balance = float(initial_balance)
    peak = balance
    max_dd = 0.0
    streak = 0
    max_streak = 0
    for p in pnls:
        balance += p
        peak = max(peak, balance)
        if peak > 0:
            max_dd = max(max_dd, (peak - balance) / peak * 100)
        streak = streak + 1 if p < 0 else 0
        max_streak = max(max_streak, streak)

    net = sum(pnls)
    return {
        "trades": n,
        "win_rate_pct": len(wins) / n * 100,
        "profit_factor": profit_factor,
        "net_profit": net,
        "return_pct": net / initial_balance * 100,
        "final_balance": balance,
        "max_drawdown_pct": max_dd,
        "expectancy": net / n,
        "avg_win": gross_profit / len(wins) if wins else 0.0,
        "avg_loss": -gross_loss / len(losses) if losses else 0.0,
        "max_losing_streak": max_streak,
    }