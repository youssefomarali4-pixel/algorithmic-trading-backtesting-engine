"""
ema_crossover.py
وظيفته: يحسب EMA و ATR ويولّد إشارات شراء/بيع من تقاطع المتوسطين.

قاعدة مهمة (لتجنب الغش في الباكتيست):
الإشارة بتتحسب على شمعة *مقفولة*، والتنفيذ بيكون على فتح الشمعة اللي بعدها.
وفي التشغيل اللايف، الشمعة الأخيرة اللي MT5 بيرجعها لسه بتتكوّن،
فلازم نحذفها قبل ما نحسب الإشارات.
"""
import pandas as pd

REQUIRED_COLUMNS = {"open", "high", "low", "close"}


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """المتوسط المتحرك الأسي (EMA)."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    ATR بطريقة Wilder: متوسط "المدى الحقيقي" (True Range)،
    وهو أكبر قيمة من التلاتة:
      1) high - low
      2) |high - إغلاق الشمعة السابقة|
      3) |low  - إغلاق الشمعة السابقة|
    """
    prev_close = df["close"].shift(1)
    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False).mean()


def generate_signals(
    df: pd.DataFrame, fast: int, slow: int, atr_period: int = 14
) -> pd.DataFrame:
    """
    يرجع نسخة من الجدول مضاف لها الأعمدة:
      ema_fast, ema_slow, atr, signal
    signal:  1 = شراء | -1 = بيع | 0 = لا شيء
    """
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"أعمدة ناقصة في البيانات: {sorted(missing)}")
    if fast >= slow:
        raise ValueError("fast لازم يكون أصغر من slow.")

    out = df.copy()
    out["ema_fast"] = calculate_ema(out["close"], fast)
    out["ema_slow"] = calculate_ema(out["close"], slow)
    out["atr"] = calculate_atr(out, atr_period)

    diff = out["ema_fast"] - out["ema_slow"]
    prev_diff = diff.shift(1)

    out["signal"] = 0
    # شراء: السريع عدّى فوق البطيء في الشمعة دي
    out.loc[(diff > 0) & (prev_diff <= 0), "signal"] = 1
    # بيع: السريع نزل تحت البطيء في الشمعة دي
    out.loc[(diff < 0) & (prev_diff >= 0), "signal"] = -1

    # أول شموع المؤشرات بتكون غير مستقرة، فنتجاهل إشاراتها
    warmup = max(slow, atr_period)
    out.iloc[:warmup, out.columns.get_loc("signal")] = 0
    return out