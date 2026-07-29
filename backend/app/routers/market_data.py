"""Market data and chart API router."""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.services.data_fetcher import fetch_ohlcv, search_tickers, get_current_price
from app.services.indicators import get_chart_data, calculate_indicators
from app.services.confluence import check_confluence

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/market", tags=["Market Data"])


@router.get("/chart/{ticker}")
async def get_chart(
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
async def get_indicators(
    ticker: str,
    mode: str = Query("intraday", pattern=r"^(intraday|short_selling|long_term)$"),
):
    """Get current indicator values and confluence status for a ticker."""
    # Determine interval and period based on mode
    if mode in ("intraday", "short_selling"):
        interval, period = "5m", "5d"
    else:
        interval, period = "1d", "1y"

    df = fetch_ohlcv(ticker, interval=interval, period=period)
    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No market data available for {ticker}",
        )

    indicators = calculate_indicators(df, mode=mode)
    if indicators is None:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient data to calculate indicators for {ticker}",
        )

    confluence = check_confluence(indicators, mode)

    return {
        "ticker": ticker.upper().replace(".NS", ""),
        "mode": mode,
        "price": indicators.price,
        "indicators": {
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
        },
        "confluence": {
            "is_aligned": confluence.is_aligned,
            "checks": confluence.checks,
            "details": confluence.details,
        },
    }


@router.get("/search")
async def search_stocks(
    q: str = Query(..., min_length=1, description="Search query"),
):
    """Search for NSE tickers by name or symbol."""
    results = search_tickers(q)
    if not results:
        return {"results": [], "query": q}
    return {"results": results, "query": q}


@router.get("/price/{ticker}")
async def get_price(ticker: str):
    """Get the latest price for a ticker."""
    price = get_current_price(ticker)
    if price is None:
        raise HTTPException(status_code=404, detail=f"Price not available for {ticker}")
    return {
        "ticker": ticker.upper().replace(".NS", ""),
        "price": price,
    }
