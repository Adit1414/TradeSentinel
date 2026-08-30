"""Market data and chart API router."""

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List
import concurrent.futures

from app.services.data_fetcher import fetch_ohlcv, search_tickers, get_current_price
from app.services.indicators import get_chart_data, calculate_indicators
from app.services.confluence import check_confluence

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/market", tags=["Market Data"])

class BatchIndicatorRequest(BaseModel):
    tickers: List[str]
    mode: str = "intraday"

@router.get("/chart/{ticker}")
def get_chart(
    ticker: str,
    interval: str = Query("5m", pattern=r"^(1m|5m|15m|1h|1d|1wk)$"),
    period: str = Query("5d"),
    mode: str = Query("intraday", pattern=r"^(intraday|short_selling|long_term)$"),
):
    """
    Get OHLCV candle data + all indicator series for charting.

    Returns data in TradingView Lightweight Charts format.
    """
    df = fetch_ohlcv(ticker, interval=interval, period=period)
    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No market data available for {ticker}",
        )

    chart_data = get_chart_data(df, mode=mode)
    chart_data["ticker"] = ticker.upper().replace(".NS", "")
    chart_data["interval"] = interval
    chart_data["period"] = period
    chart_data["mode"] = mode

    return chart_data


@router.get("/indicators/{ticker}")
def get_indicators(
    ticker: str,
    mode: str = Query("intraday", pattern=r"^(intraday|short_selling|long_term)$"),
):
    """Get current indicator values and confluence status for a ticker."""
    res = _get_single_indicator(ticker, mode)
    if res is None:
        raise HTTPException(status_code=404, detail=f"No market data or insufficient data for {ticker}")
    return res

@router.post("/indicators/batch")
def get_indicators_batch(request: BatchIndicatorRequest):
    """Get indicators for multiple tickers concurrently."""
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_ticker = {
            executor.submit(_get_single_indicator, t, request.mode): t 
            for t in request.tickers
        }
        for future in concurrent.futures.as_completed(future_to_ticker):
            t = future_to_ticker[future]
            try:
                res = future.result()
                if res:
                    results[t] = res
            except Exception as e:
                logger.error(f"Batch indicator error for {t}: {e}")
    return results

def _get_single_indicator(ticker: str, mode: str) -> dict:
    """Helper to fetch and calculate indicators for a single ticker."""
    # Determine interval and period based on mode
    if mode in ("intraday", "short_selling"):
        interval, period = "5m", "5d"
    else:  # long_term — weekly candles, 5 years for 200-W SMA
        interval, period = "1wk", "5y"

    df = fetch_ohlcv(ticker, interval=interval, period=period)
    if df.empty:
        return None

    indicators = calculate_indicators(df, mode=mode)
    if indicators is None:
        return None

    confluence = check_confluence(indicators, mode)

    # Base response shared by all modes
    response = {
        "ticker": ticker.upper().replace(".NS", ""),
        "mode": mode,
        "price": indicators.price,
        "confluence": {
            "is_aligned": confluence.is_aligned,
            "signal": confluence.signal,
            "indicator_signals": confluence.indicator_signals,
            "details": confluence.details,
        },
    }

    if mode == "long_term":
        # Long-Term: return weekly macro indicators
        response["indicators"] = {
            "weekly_sma_200": indicators.weekly_sma_200,
            "weekly_rsi": indicators.rsi,
            "weekly_bb_lower": indicators.weekly_bb_lower,
            "weekly_bb_mid": indicators.weekly_bb_mid,
            "weekly_bb_upper": indicators.weekly_bb_upper,
            "macd": {
                "line": indicators.macd_line,
                "signal": indicators.macd_signal,
                "histogram": indicators.macd_histogram,
                "crossover": indicators.macd_crossover,
            },
        }
    else:
        # Intraday / Short-Selling: return 5-min indicators
        response["indicators"] = {
            "vwap": indicators.vwap,
            "ema_200": indicators.ema_200,
            "supertrend": {
                "value": indicators.supertrend_value,
                "direction": indicators.supertrend_direction,
                "label": "Bullish" if indicators.supertrend_direction == 1 else "Bearish",
            },
            "rsi": {
                "value": indicators.rsi,
                "rising": indicators.rsi_rising,
            },
            "macd": {
                "line": indicators.macd_line,
                "signal": indicators.macd_signal,
                "histogram": indicators.macd_histogram,
                "crossover": indicators.macd_crossover,
            },
        }

    return response


@router.get("/search")
def search_stocks(
    q: str = Query(..., min_length=1, description="Search query"),
):
    """Search for NSE tickers by name or symbol."""
    results = search_tickers(q)
    if not results:
        return {"results": [], "query": q}
    return {"results": results, "query": q}


@router.get("/price/{ticker}")
def get_price(ticker: str):
    """Get the latest price for a ticker."""
    price = get_current_price(ticker)
    if price is None:
        raise HTTPException(status_code=404, detail=f"Price not available for {ticker}")
    return {
        "ticker": ticker.upper().replace(".NS", ""),
        "price": price,
    }
