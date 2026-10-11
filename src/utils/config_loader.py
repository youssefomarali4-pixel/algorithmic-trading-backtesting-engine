"""
config_loader.py
وظيفته: يقرأ ملف config/settings.yaml ويحوله لكائنات بايثون منظمة،
عشان كل ملفات البوت تاخد الإعدادات من مكان واحد بس.
"""
from dataclasses import dataclass
from pathlib import Path
import yaml

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT_DIR / "config" / "settings.yaml"
VALID_TIMEFRAMES = {"M1", "M5", "M15", "M30", "H1", "H4", "D1"}

@dataclass(frozen=True)
class MT5Config:
    symbol: str
    timeframe: str
    history_bars: int

@dataclass(frozen=True)
class StrategyConfig:
    name: str
    ema_fast: int
    ema_slow: int

@dataclass(frozen=True)
class RiskConfig:
    risk_per_trade_percent: float
    max_daily_loss_percent: float
    sl_atr_multiplier: float
    rr_ratio: float

@dataclass(frozen=True)
class BacktestConfig:
    initial_balance: float
    commission_per_lot: float

@dataclass(frozen=True)
class Settings:
    mode: str
    mt5: MT5Config
    strategy: StrategyConfig
    risk: RiskConfig
    backtest: BacktestConfig

def _validate(s: Settings) -> None:
    """فحوصات أمان: لو أي شرط اتكسر نوقف البوت برسالة واضحة."""
    if s.mode != "demo":
        raise ValueError("الوضع المسموح حالياً هو demo فقط.")
    if s.mt5.timeframe not in VALID_TIMEFRAMES:
        raise ValueError(f"الفريم '{s.mt5.timeframe}' غير مدعوم. المتاح: {sorted(VALID_TIMEFRAMES)}")
    if s.mt5.history_bars <= 0:
        raise ValueError("history_bars لازم يكون أكبر من صفر.")
    if s.strategy.ema_fast >= s.strategy.ema_slow:
        raise ValueError("ema_fast لازم يكون أصغر من ema_slow.")
    if not (0 < s.risk.risk_per_trade_percent <= 5):
        raise ValueError("risk_per_trade_percent لازم يكون بين 0 و 5.")
    if s.risk.max_daily_loss_percent <= 0:
        raise ValueError("max_daily_loss_percent لازم يكون أكبر من صفر.")
    if s.risk.sl_atr_multiplier <= 0 or s.risk.rr_ratio <= 0:
        raise ValueError("sl_atr_multiplier و rr_ratio لازم يكونوا أكبر من صفر.")
    if s.backtest.initial_balance <= 0:
        raise ValueError("initial_balance لازم يكون أكبر من صفر.")

def load_settings(path: Path = DEFAULT_CONFIG_PATH) -> Settings:
    """يقرأ ملف الإعدادات ويرجع كائن Settings جاهز للاستخدام."""
    if not path.exists():
        raise FileNotFoundError(f"ملف الإعدادات مش موجود: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    try:
        settings = Settings(
            mode=raw["mode"],
            mt5=MT5Config(**raw["mt5"]),
            strategy=StrategyConfig(**raw["strategy"]),
            risk=RiskConfig(**raw["risk"]),
            backtest=BacktestConfig(**raw["backtest"]),
        )
    except (KeyError, TypeError) as e:
        raise ValueError(f"فيه مشكلة في ملف الإعدادات (قسم ناقص أو اسم غلط): {e}") from e
    _validate(settings)
    return settings