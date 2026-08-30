"""4-indicator confluence checker.

Implements strict alignment rules for each trading mode:
- Intraday (Buy side) — bullish confluence on 5-min
- Short Selling (Sell side) — bearish confluence on 5-min
- Long-Term (Delivery) — bullish confluence on daily
"""

import logging
from dataclasses import dataclass
from typing import Optional

from app.services.indicators import IndicatorResult

logger = logging.getLogger(__name__)


@dataclass
class ConfluenceResult:
    """Result of a confluence check."""
    is_aligned: bool = False
    mode: str = ""
    signal: str = "NONE" # "BUY" | "SELL" | "NONE"
    indicator_signals: dict = None # e.g. {"rsi": "BUY", "macd": "NEUTRAL"}
    details: dict = None  # Human-readable summary

    def __post_init__(self):
        if self.indicator_signals is None:
            self.indicator_signals = {}
        if self.details is None:
            self.details = {}


def check_confluence(indicators: IndicatorResult, mode: str) -> ConfluenceResult:
    """
    Check if indicators are aligned for the given timeframe.
    Evaluates each indicator into a BUY/SELL/NEUTRAL state.
    """
    if indicators is None:
        return ConfluenceResult(is_aligned=False, mode=mode, signal="NONE")

    indicator_signals = {}
    details = {}

    if mode == "intraday":
        # 1. VWAP
        if indicators.vwap is not None:
            if indicators.price > indicators.vwap:
                indicator_signals["vwap"] = "BUY"
            else:
                indicator_signals["vwap"] = "SELL"
            details["vwap"] = f"Price ₹{indicators.price:.2f} vs VWAP ₹{indicators.vwap:.2f}"
        else:
            indicator_signals["vwap"] = "NEUTRAL"
            details["vwap"] = "VWAP not available"

        # 2. Supertrend
        if indicators.supertrend_direction == 1:
            indicator_signals["supertrend"] = "BUY"
            details["supertrend"] = f"Bullish (Green) at ₹{indicators.supertrend_value:.2f}"
        else:
            indicator_signals["supertrend"] = "SELL"
            details["supertrend"] = f"Bearish (Red) at ₹{indicators.supertrend_value:.2f}"

        # 3. RSI
        if 40 < indicators.rsi < 60 and indicators.rsi_rising:
            indicator_signals["rsi"] = "BUY"
        elif 33 < indicators.rsi < 50 and not indicators.rsi_rising:
            indicator_signals["rsi"] = "SELL"
        else:
            indicator_signals["rsi"] = "NEUTRAL"
        details["rsi"] = f"RSI {indicators.rsi:.1f} ({'rising' if indicators.rsi_rising else 'falling'})"

        # 4. MACD
        if indicators.macd_line > indicators.macd_signal and indicators.macd_histogram > 0:
            indicator_signals["macd"] = "BUY"
        elif indicators.macd_line < indicators.macd_signal and indicators.macd_histogram < 0:
            indicator_signals["macd"] = "SELL"
        else:
            indicator_signals["macd"] = "NEUTRAL"
        details["macd"] = f"MACD {indicators.macd_line:.4f} / Signal {indicators.macd_signal:.4f}"

        is_buy_aligned = all(v == "BUY" for v in indicator_signals.values())
        is_sell_aligned = all(v == "SELL" for v in indicator_signals.values())

        if is_buy_aligned:
            logger.info(f"🎯 INTRADAY BUY CONFLUENCE detected! Price: ₹{indicators.price:.2f}")
            return ConfluenceResult(is_aligned=True, mode=mode, signal="BUY", indicator_signals=indicator_signals, details=details)
        elif is_sell_aligned:
            logger.info(f"🎯 INTRADAY SELL CONFLUENCE detected! Price: ₹{indicators.price:.2f}")
            return ConfluenceResult(is_aligned=True, mode=mode, signal="SELL", indicator_signals=indicator_signals, details=details)
        else:
            return ConfluenceResult(is_aligned=False, mode=mode, signal="NONE", indicator_signals=indicator_signals, details=details)

    elif mode == "long_term":
        # 1. 200-W SMA Proximity
        if indicators.weekly_sma_200 is not None and indicators.weekly_sma_200 > 0:
            pct_diff = ((indicators.price - indicators.weekly_sma_200) / indicators.weekly_sma_200) * 100
            if indicators.price <= indicators.weekly_sma_200 * 1.03 and indicators.price >= indicators.weekly_sma_200 * 0.95:
                indicator_signals["weekly_sma_200"] = "BUY"
            elif indicators.price >= indicators.weekly_sma_200 * 1.35:
                indicator_signals["weekly_sma_200"] = "SELL"
            else:
                indicator_signals["weekly_sma_200"] = "NEUTRAL"
            details["weekly_sma_200"] = f"Price ₹{indicators.price:.2f} | 200-W SMA ₹{indicators.weekly_sma_200:.2f} ({pct_diff:+.1f}%)"
        else:
            indicator_signals["weekly_sma_200"] = "NEUTRAL"
            details["weekly_sma_200"] = "200-W SMA not available"

        # 2. RSI
        if indicators.rsi <= 42:
            indicator_signals["weekly_rsi"] = "BUY"
        elif indicators.rsi >= 70:
            indicator_signals["weekly_rsi"] = "SELL"
        else:
            indicator_signals["weekly_rsi"] = "NEUTRAL"
        details["weekly_rsi"] = f"Weekly RSI {indicators.rsi:.1f}"

        # 3. MACD
        macd_bullish_cross = indicators.macd_line > indicators.macd_signal
        hist_rising_from_negative = (indicators.macd_histogram > indicators.macd_histogram_prev and indicators.macd_histogram_prev < 0)
        macd_exhausted = indicators.macd_line < indicators.macd_signal
        
        if macd_bullish_cross or hist_rising_from_negative:
            indicator_signals["weekly_macd"] = "BUY"
        elif macd_exhausted:
            indicator_signals["weekly_macd"] = "SELL"
        else:
            indicator_signals["weekly_macd"] = "NEUTRAL"
        details["weekly_macd"] = f"Weekly MACD {indicators.macd_line:.4f} / Signal {indicators.macd_signal:.4f}"

        # 4. Bollinger Bands (combining upper and lower into one signal)
        if indicators.weekly_bb_lower is not None and indicators.weekly_bb_upper is not None:
            if indicators.price <= indicators.weekly_bb_lower * 1.02:
                indicator_signals["weekly_bb"] = "BUY"
                details["weekly_bb"] = f"Price ₹{indicators.price:.2f} at/near Lower BB ₹{indicators.weekly_bb_lower:.2f}"
            elif indicators.price >= indicators.weekly_bb_upper * 0.98:
                indicator_signals["weekly_bb"] = "SELL"
                details["weekly_bb"] = f"Price ₹{indicators.price:.2f} at/near Upper BB ₹{indicators.weekly_bb_upper:.2f}"
            else:
                indicator_signals["weekly_bb"] = "NEUTRAL"
                details["weekly_bb"] = f"Price ₹{indicators.price:.2f} between bands"
        else:
            indicator_signals["weekly_bb"] = "NEUTRAL"
            details["weekly_bb"] = "Bollinger Bands not available"

        buy_count = sum(1 for v in indicator_signals.values() if v == "BUY")
        sell_count = sum(1 for v in indicator_signals.values() if v == "SELL")

        if buy_count >= 3:
            logger.info(f"🎯 LONG-TERM VALUE ALERT! Price: ₹{indicators.price:.2f} | {buy_count}/4 conditions met")
            return ConfluenceResult(is_aligned=True, mode=mode, signal="BUY", indicator_signals=indicator_signals, details=details)
        elif sell_count >= 3:
            logger.info(f"🏦 LONG-TERM PROFIT-TAKING ALERT! Price: ₹{indicators.price:.2f} | {sell_count}/4 sell conditions met")
            return ConfluenceResult(is_aligned=True, mode=mode, signal="SELL", indicator_signals=indicator_signals, details=details)
        else:
            return ConfluenceResult(is_aligned=False, mode=mode, signal="NONE", indicator_signals=indicator_signals, details=details)

    else:
        logger.error(f"Unknown mode: {mode}")
        return ConfluenceResult(is_aligned=False, mode=mode, signal="NONE")

