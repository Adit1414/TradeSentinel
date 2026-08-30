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
    signal: str = "NONE" # "BUY" | "SELL" | "NONE"

    def __post_init__(self):
        if self.checks is None:
            self.checks = {}
        if self.details is None:
            self.details = {}


def check_confluence(indicators: IndicatorResult, mode: str) -> ConfluenceResult:
    """
    Check if indicators are aligned for the given timeframe.

    Args:
        indicators: Calculated indicator values from the indicator engine.
        mode: "intraday" or "long_term".

    Returns:
        ConfluenceResult with alignment status, per-indicator details, and signal.
    """
    if indicators is None:
        return ConfluenceResult(is_aligned=False, mode=mode, signal="NONE")

    if mode == "intraday":
        buy_res = _check_intraday(indicators)
        sell_res = _check_short_selling(indicators)
        
        if buy_res.is_aligned:
            buy_res.signal = "BUY"
            return buy_res
        elif sell_res.is_aligned:
            sell_res.signal = "SELL"
            return sell_res
        else:
            buy_res.signal = "NONE"
            return buy_res

    elif mode == "long_term":
        buy_res = _check_long_term(indicators)
        sell_res = _check_long_term_sell(indicators)
        
        if buy_res.is_aligned:
            buy_res.signal = "BUY"
            return buy_res
        elif sell_res.is_aligned:
            sell_res.signal = "SELL"
            return sell_res
        else:
            buy_res.signal = "NONE"
            return buy_res

    else:
        logger.error(f"Unknown mode: {mode}")
        return ConfluenceResult(is_aligned=False, mode=mode, signal="NONE")


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
    Long-Term (Delivery) macro "Buy-the-Dip" confluence on weekly timeframe.

    Fires a LONG-TERM VALUE ALERT when at least 3 of the following 4
    weekly conditions align (3-of-4 threshold):

    1. Near 200-Week SMA  — price within [SMA*0.95, SMA*1.03]
    2. Weekly RSI ≤ 42    — severely discounted zone (not overbought)
    3. Weekly MACD Recovery — MACD > Signal (bullish cross)
                              OR histogram rising from negative territory
    4. Weekly BB Lower Touch — price ≤ Lower Bollinger Band * 1.02
    """
    checks = {}
    details = {}

    # 1. 200-Week SMA Proximity check
    if ind.weekly_sma_200 is not None and ind.weekly_sma_200 > 0:
        near_sma = (ind.price <= ind.weekly_sma_200 * 1.03 and
                    ind.price >= ind.weekly_sma_200 * 0.95)
        checks["weekly_sma_200"] = near_sma
        pct_diff = ((ind.price - ind.weekly_sma_200) / ind.weekly_sma_200) * 100
        details["weekly_sma_200"] = (
            f"Price ₹{ind.price:.2f} | 200-W SMA ₹{ind.weekly_sma_200:.2f} "
            f"({pct_diff:+.1f}%) — "
            f"{'✓ Near major support' if near_sma else '✗ Outside proximity zone'}"
        )
    else:
        checks["weekly_sma_200"] = False
        details["weekly_sma_200"] = "200-W SMA not available (need 200+ weekly candles)"

    # 2. Weekly RSI ≤ 42 (severely discounted / oversold zone)
    rsi_discounted = ind.rsi <= 42
    checks["weekly_rsi"] = rsi_discounted
    details["weekly_rsi"] = (
        f"Weekly RSI {ind.rsi:.1f} — "
        f"{'✓ Discounted zone (≤42)' if rsi_discounted else f'✗ Not discounted ({ind.rsi:.1f} > 42)'}"
    )

    # 3. Weekly MACD Recovery — bullish cross OR histogram rising from negative
    macd_bullish_cross = ind.macd_line > ind.macd_signal
    hist_rising_from_negative = (
        ind.macd_histogram > ind.macd_histogram_prev and
        ind.macd_histogram_prev < 0
    )
    macd_recovery = macd_bullish_cross or hist_rising_from_negative
    checks["weekly_macd"] = macd_recovery
    if macd_bullish_cross:
        macd_reason = "✓ MACD bullish crossover"
    elif hist_rising_from_negative:
        macd_reason = "✓ Histogram rising from negative (momentum shift)"
    else:
        macd_reason = "✗ No bullish recovery signal"
    details["weekly_macd"] = (
        f"Weekly MACD {ind.macd_line:.4f} / Signal {ind.macd_signal:.4f} — {macd_reason}"
    )

    # 4. Weekly Bollinger Lower Band Touch — price ≤ Lower Band * 1.02
    if ind.weekly_bb_lower is not None and ind.weekly_bb_lower > 0:
        bb_touch = ind.price <= ind.weekly_bb_lower * 1.02
        checks["weekly_bb_lower"] = bb_touch
        details["weekly_bb_lower"] = (
            f"Price ₹{ind.price:.2f} | Lower BB ₹{ind.weekly_bb_lower:.2f} — "
            f"{'✓ At/near lower band (mean-reversion zone)' if bb_touch else '✗ Above lower Bollinger Band'}"
        )
    else:
        checks["weekly_bb_lower"] = False
        details["weekly_bb_lower"] = "Bollinger Bands not available (need 20+ weekly candles)"

    # 3-of-4 threshold (macro confluence — not all 4 required)
    aligned_count = sum(checks.values())
    is_aligned = aligned_count >= 3

    if is_aligned:
        logger.info(
            f"🎯 LONG-TERM VALUE ALERT! Price: ₹{ind.price:.2f} "
            f"| {aligned_count}/4 weekly conditions met"
        )

    return ConfluenceResult(
        is_aligned=is_aligned,
        mode="long_term",
        checks=checks,
        details=details,
    )


def _check_long_term_sell(ind: IndicatorResult) -> ConfluenceResult:
    """
    Long-Term (Delivery) "Exit/Profit-Booking" confluence on weekly timeframe.

    Fires a LONG-TERM SELL ALERT when at least 3 of the following 4
    weekly conditions align (3-of-4 threshold):

    1. Weekly RSI >= 70 (Asset is euphoric/overextended).
    2. Weekly Upper Bollinger Band Touch (current_price >= weekly_bb_upper * 0.98).
    3. Weekly MACD Exhaustion (weekly_macd_line < weekly_macd_signal).
    4. 200-W SMA Overextension (current_price >= weekly_sma_200 * 1.35).
    """
    checks = {}
    details = {}

    # 1. Weekly RSI >= 70
    rsi_overbought = ind.rsi >= 70
    checks["weekly_rsi"] = rsi_overbought
    details["weekly_rsi"] = (
        f"Weekly RSI {ind.rsi:.1f} — "
        f"{'✓ Overbought zone (>=70)' if rsi_overbought else f'✗ Not overbought ({ind.rsi:.1f} < 70)'}"
    )

    # 2. Weekly Upper Bollinger Band Touch
    if ind.weekly_bb_upper is not None and ind.weekly_bb_upper > 0:
        bb_touch = ind.price >= ind.weekly_bb_upper * 0.98
        checks["weekly_bb_upper"] = bb_touch
        details["weekly_bb_upper"] = (
            f"Price ₹{ind.price:.2f} | Upper BB ₹{ind.weekly_bb_upper:.2f} — "
            f"{'✓ Near/above upper band' if bb_touch else '✗ Below upper Bollinger Band'}"
        )
    else:
        checks["weekly_bb_upper"] = False
        details["weekly_bb_upper"] = "Bollinger Bands not available"

    # 3. Weekly MACD Exhaustion
    macd_exhausted = ind.macd_line < ind.macd_signal
    checks["weekly_macd"] = macd_exhausted
    details["weekly_macd"] = (
        f"Weekly MACD {ind.macd_line:.4f} / Signal {ind.macd_signal:.4f} — "
        f"{'✓ Momentum rolling over (Bearish cross)' if macd_exhausted else '✗ Bullish momentum intact'}"
    )

    # 4. 200-W SMA Overextension
    if ind.weekly_sma_200 is not None and ind.weekly_sma_200 > 0:
        sma_overextended = ind.price >= ind.weekly_sma_200 * 1.35
        checks["weekly_sma_200"] = sma_overextended
        pct_diff = ((ind.price - ind.weekly_sma_200) / ind.weekly_sma_200) * 100
        details["weekly_sma_200"] = (
            f"Price ₹{ind.price:.2f} | 200-W SMA ₹{ind.weekly_sma_200:.2f} "
            f"(+{pct_diff:.1f}%) — "
            f"{'✓ Overextended (>35%)' if sma_overextended else '✗ Not overextended (<35%)'}"
        )
    else:
        checks["weekly_sma_200"] = False
        details["weekly_sma_200"] = "200-W SMA not available"

    aligned_count = sum(checks.values())
    is_aligned = aligned_count >= 3

    if is_aligned:
        logger.info(
            f"🏦 LONG-TERM PROFIT-TAKING ALERT! Price: ₹{ind.price:.2f} "
            f"| {aligned_count}/4 weekly sell conditions met"
        )

    return ConfluenceResult(
        is_aligned=is_aligned,
        mode="long_term_sell",
        checks=checks,
        details=details,
    )

