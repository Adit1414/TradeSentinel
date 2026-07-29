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
    checks: dict = None  # Individual indicator pass/fail
    details: dict = None  # Human-readable summary

    def __post_init__(self):
        if self.checks is None:
            self.checks = {}
        if self.details is None:
            self.details = {}


def check_confluence(indicators: IndicatorResult, mode: str) -> ConfluenceResult:
    """
    Check if all 4 indicators are perfectly aligned for the given mode.

    Args:
        indicators: Calculated indicator values from the indicator engine.
        mode: "intraday", "short_selling", or "long_term".

    Returns:
        ConfluenceResult with alignment status and per-indicator details.
    """
    if indicators is None:
        return ConfluenceResult(is_aligned=False, mode=mode)

    if mode == "intraday":
        return _check_intraday(indicators)
    elif mode == "short_selling":
        return _check_short_selling(indicators)
    elif mode == "long_term":
        return _check_long_term(indicators)
    else:
        logger.error(f"Unknown mode: {mode}")
        return ConfluenceResult(is_aligned=False, mode=mode)


def _check_intraday(ind: IndicatorResult) -> ConfluenceResult:
    """
    Intraday (Buy side) confluence on 5-minute timeframe:
    1. Price > VWAP
    2. Supertrend bullish (direction == 1, line below price)
    3. RSI rising and between 40-60
    4. MACD bullish crossover
    """
    checks = {}
    details = {}

    # 1. VWAP check
    if ind.vwap is not None:
        checks["vwap"] = ind.price > ind.vwap
        details["vwap"] = (
            f"Price ₹{ind.price:.2f} {'>' if checks['vwap'] else '<='} "
            f"VWAP ₹{ind.vwap:.2f}"
        )
    else:
        checks["vwap"] = False
        details["vwap"] = "VWAP not available"

    # 2. Supertrend check
    checks["supertrend"] = ind.supertrend_direction == 1
    details["supertrend"] = (
        f"Supertrend {'Bullish (Green)' if checks['supertrend'] else 'Bearish (Red)'} "
        f"at ₹{ind.supertrend_value:.2f}"
    )

    # 3. RSI check — rising and between 40-60
    rsi_in_range = 40 < ind.rsi < 60
    checks["rsi"] = rsi_in_range and ind.rsi_rising
    details["rsi"] = (
        f"RSI {ind.rsi:.1f} ({'rising' if ind.rsi_rising else 'falling'}) — "
        f"{'in zone 40-60' if rsi_in_range else 'outside zone 40-60'}"
    )

    # 4. MACD bullish state
    checks["macd"] = ind.macd_line > ind.macd_signal and ind.macd_histogram > 0
    details["macd"] = (
        f"MACD {'Bullish ✓' if checks['macd'] else 'Not bullish'} "
        f"(MACD: {ind.macd_line:.4f}, Signal: {ind.macd_signal:.4f})"
    )

    is_aligned = all(checks.values())
    if is_aligned:
        logger.info(f"🎯 INTRADAY CONFLUENCE detected! Price: ₹{ind.price:.2f}")

    return ConfluenceResult(
        is_aligned=is_aligned,
        mode="intraday",
        checks=checks,
        details=details,
    )


def _check_short_selling(ind: IndicatorResult) -> ConfluenceResult:
    """
    Short Selling (Sell side) confluence on 5-minute timeframe:
    1. Price < VWAP
    2. Supertrend bearish (direction == -1, line above price)
    3. RSI falling and between 33 and 50 (33 < RSI < 50)
    4. MACD bearish crossover
    """
    checks = {}
    details = {}

    # 1. VWAP check
    if ind.vwap is not None:
        checks["vwap"] = ind.price < ind.vwap
        details["vwap"] = (
            f"Price ₹{ind.price:.2f} {'<' if checks['vwap'] else '>='} "
            f"VWAP ₹{ind.vwap:.2f}"
        )
    else:
        checks["vwap"] = False
        details["vwap"] = "VWAP not available"

    # 2. Supertrend check
    checks["supertrend"] = ind.supertrend_direction == -1
    details["supertrend"] = (
        f"Supertrend {'Bearish (Red)' if checks['supertrend'] else 'Bullish (Green)'} "
        f"at ₹{ind.supertrend_value:.2f}"
    )

    # 3. RSI check — falling and between 33 and 50 (>33 & <50)
    rsi_in_range = 33 < ind.rsi < 50
    checks["rsi"] = rsi_in_range and not ind.rsi_rising
    details["rsi"] = (
        f"RSI {ind.rsi:.1f} ({'falling' if not ind.rsi_rising else 'rising'}) — "
        f"{'in zone 33-50' if rsi_in_range else 'outside zone 33-50'}"
    )

    # 4. MACD bearish state
    checks["macd"] = ind.macd_line < ind.macd_signal and ind.macd_histogram < 0
    details["macd"] = (
        f"MACD {'Bearish ✓' if checks['macd'] else 'Not bearish'} "
        f"(MACD: {ind.macd_line:.4f}, Signal: {ind.macd_signal:.4f})"
    )

    is_aligned = all(checks.values())
    if is_aligned:
        logger.info(f"🎯 SHORT SELLING CONFLUENCE detected! Price: ₹{ind.price:.2f}")

    return ConfluenceResult(
        is_aligned=is_aligned,
        mode="short_selling",
        checks=checks,
        details=details,
    )


def _check_long_term(ind: IndicatorResult) -> ConfluenceResult:
    """
    Long-Term (Delivery) confluence on daily timeframe:
    1. Price > 200 EMA
    2. Supertrend bullish (direction == 1)
    3. RSI > 50, rising, and not overbought (< 70)
    4. MACD bullish crossover on daily
    """
    checks = {}
    details = {}

    # 1. 200 EMA check
    if ind.ema_200 is not None:
        checks["ema_200"] = ind.price > ind.ema_200
        details["ema_200"] = (
            f"Price ₹{ind.price:.2f} {'>' if checks['ema_200'] else '<='} "
            f"200 EMA ₹{ind.ema_200:.2f}"
        )
    else:
        checks["ema_200"] = False
        details["ema_200"] = "200 EMA not available (need 200+ daily candles)"

    # 2. Supertrend check
    checks["supertrend"] = ind.supertrend_direction == 1
    details["supertrend"] = (
        f"Supertrend {'Bullish (Green)' if checks['supertrend'] else 'Bearish (Red)'} "
        f"at ₹{ind.supertrend_value:.2f}"
    )

    # 3. RSI check — above 50, rising, not overbought
    rsi_ok = 50 < ind.rsi < 70
    checks["rsi"] = rsi_ok and ind.rsi_rising
    details["rsi"] = (
        f"RSI {ind.rsi:.1f} ({'rising' if ind.rsi_rising else 'falling'}) — "
        f"{'in zone 50-70' if rsi_ok else 'outside zone 50-70'}"
    )

    # 4. MACD bullish state
    checks["macd"] = ind.macd_line > ind.macd_signal and ind.macd_histogram > 0
    details["macd"] = (
        f"MACD {'Bullish ✓' if checks['macd'] else 'Not bullish'} "
        f"(MACD: {ind.macd_line:.4f}, Signal: {ind.macd_signal:.4f})"
    )

    is_aligned = all(checks.values())
    if is_aligned:
        logger.info(f"🎯 LONG-TERM CONFLUENCE detected! Price: ₹{ind.price:.2f}")

    return ConfluenceResult(
        is_aligned=is_aligned,
        mode="long_term",
        checks=checks,
        details=details,
    )
