"""Paper trade service — snapshot fetching, break-even, stop-loss, and PnL logic.

All NSE fee calculations reuse the existing charges utility so the numbers
are consistent with the Positions / break-even calculator.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.data_fetcher import fetch_ohlcv
from app.services.indicators import calculate_indicators
from app.utils.charges import calc_charges_intraday, calc_charges_delivery

logger = logging.getLogger(__name__)


# ── Snapshot ──────────────────────────────────────────────────────────────────

def fetch_snapshot(ticker: str, mode: str = "intraday") -> Optional[dict]:
    """
    Fetch the latest OHLCV data and compute all 4 indicators for a ticker.

    Args:
        ticker: NSE stock symbol (e.g. "RELIANCE").
        mode: "intraday" | "short_selling" | "long_term" — determines data
              interval, period, and which overlay indicator is calculated.

    Returns:
        Dict with price and indicator snapshot, or None on failure.
    """
    # Choose interval/period based on mode (mirrors market_data router)
    if mode in ("intraday", "short_selling"):
        interval, period = "5m", "5d"
    else:
        interval, period = "1d", "1y"

    df = fetch_ohlcv(ticker, interval=interval, period=period, use_cache=False)
    if df.empty:
        logger.warning(f"No OHLCV data for {ticker} (mode={mode})")
        return None

    result = calculate_indicators(df, mode=mode)
    if result is None:
        logger.warning(f"Could not calculate indicators for {ticker}")
        return None

    clean_ticker = ticker.upper().replace(".NS", "")

    return {
        "ticker": clean_ticker,
        "mode": mode,
        "price": round(result.price, 2),
        "rsi": round(result.rsi, 2),
        "macd_fast": round(result.macd_line, 4),
        "macd_signal": round(result.macd_signal, 4),
        "vwap": round(result.vwap, 2) if result.vwap is not None else None,
        "supertrend": round(result.supertrend_value, 2),
        "ema_200": round(result.ema_200, 2) if result.ema_200 is not None else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Break-Even & Stop-Loss ─────────────────────────────────────────────────────

def calculate_break_even_and_sl(
    trade_direction: str,
    entry_price: float,
    quantity: int,
    vwap: Optional[float] = None,
    supertrend: Optional[float] = None,
    ema_200: Optional[float] = None,
) -> dict:
    """
    Calculate the exact NSE-fee-adjusted break-even price and a suggested
    stop-loss level for the given trade direction.

    Returns:
        Dict with keys: break_even_price, suggested_stop_loss_price,
        total_entry_fees, total_exit_fees.
    """
    is_delivery = trade_direction == "LONG_TERM"
    calc_fn = calc_charges_delivery if is_delivery else calc_charges_intraday

    turnover = entry_price * quantity

    if trade_direction == "INTRADAY_BUY":
        # Buyer pays: buy-side charges on entry + sell-side charges on exit
        entry_charges = calc_fn(turnover, "BUY")
        # Estimate exit at roughly entry price for fee purposes
        exit_charges = calc_fn(turnover, "SELL")
        total_fees = entry_charges["total"] + exit_charges["total"]
        break_even_price = entry_price + (total_fees / quantity)

        # SL: prefer VWAP; fallback to 0.5% below entry
        if vwap is not None:
            suggested_sl = vwap
        else:
            suggested_sl = entry_price * 0.995

    elif trade_direction == "SHORT_SELL":
        # Seller receives: sell-side charges on entry + buy-side charges on cover
        entry_charges = calc_fn(turnover, "SELL")
        exit_charges = calc_fn(turnover, "BUY")
        total_fees = entry_charges["total"] + exit_charges["total"]
        # For a short, break-even is the price you need to cover at or below
        break_even_price = entry_price - (total_fees / quantity)

        # SL: if VWAP > entry (price breaking above) use VWAP; else supertrend
        if vwap is not None and vwap > entry_price:
            suggested_sl = vwap
        elif supertrend is not None:
            suggested_sl = supertrend
        else:
            suggested_sl = entry_price * 1.005  # 0.5% risk above entry

    else:  # LONG_TERM (CNC Delivery)
        entry_charges = calc_fn(turnover, "BUY")
        exit_charges = calc_fn(turnover, "SELL")
        total_fees = entry_charges["total"] + exit_charges["total"]
        break_even_price = entry_price + (total_fees / quantity)

        # SL: prefer EMA 200; fallback to 2% below entry
        if ema_200 is not None:
            suggested_sl = ema_200
        else:
            suggested_sl = entry_price * 0.98

    return {
        "break_even_price": round(break_even_price, 2),
        "suggested_stop_loss_price": round(suggested_sl, 2),
        "total_entry_fees": round(entry_charges["total"], 2),
        "total_exit_fees": round(exit_charges["total"], 2),
    }


# ── PnL on Close ──────────────────────────────────────────────────────────────

def compute_close_pnl(
    trade_direction: str,
    entry_price: float,
    exit_price: float,
    quantity: int,
) -> dict:
    """
    Calculate gross and net-after-fees PnL when closing a paper trade.

    For INTRADAY_BUY / LONG_TERM:   profit = (exit - entry) × qty − fees
    For SHORT_SELL:                  profit = (entry - exit) × qty − fees

    Returns:
        Dict with pnl_gross and pnl_net_after_fees.
    """
    is_delivery = trade_direction == "LONG_TERM"
    calc_fn = calc_charges_delivery if is_delivery else calc_charges_intraday

    entry_turnover = entry_price * quantity
    exit_turnover = exit_price * quantity

    if trade_direction in ("INTRADAY_BUY", "LONG_TERM"):
        pnl_gross = (exit_price - entry_price) * quantity
        entry_fees = calc_fn(entry_turnover, "BUY")["total"]
        exit_fees = calc_fn(exit_turnover, "SELL")["total"]

    else:  # SHORT_SELL
        pnl_gross = (entry_price - exit_price) * quantity
        entry_fees = calc_fn(entry_turnover, "SELL")["total"]
        exit_fees = calc_fn(exit_turnover, "BUY")["total"]

    pnl_net = pnl_gross - entry_fees - exit_fees

    return {
        "pnl_gross": round(pnl_gross, 2),
        "pnl_net_after_fees": round(pnl_net, 2),
    }
