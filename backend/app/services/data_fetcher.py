"""yfinance wrapper with in-memory caching for NSE stock data."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# In-memory cache: key = (ticker, interval, period) → (timestamp, dataframe)
_cache: dict[tuple, tuple[datetime, pd.DataFrame]] = {}
_CACHE_TTL_SECONDS = {
    "1m": 30,
    "5m": 60,
    "15m": 120,
    "1h": 300,
    "1d": 600,
    "1wk": 3600,
}


def _nse_ticker(ticker: str) -> str:
    """Ensure the ticker has the .NS suffix for NSE."""
    ticker = ticker.strip().upper()
    if not ticker.endswith(".NS"):
        ticker = f"{ticker}.NS"
    return ticker


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to lowercase for pandas-ta compatibility."""
    # yfinance may return MultiIndex columns; flatten if so
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]
    return df


def fetch_ohlcv(
    ticker: str,
    interval: str = "5m",
    period: str = "5d",
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Fetch OHLCV data for an NSE ticker via yfinance.

    Args:
        ticker: NSE stock symbol (e.g. "RELIANCE" or "RELIANCE.NS").
        interval: Candle interval — "1m", "5m", "15m", "1h", "1d", "1wk".
        period: Lookback period — "1d", "5d", "1mo", "3mo", "6mo", "1y", "max".
        use_cache: Whether to use the in-memory cache.

    Returns:
        Cleaned pandas DataFrame with columns: open, high, low, close, volume.
        Index is a DatetimeIndex.
    """
    nse_sym = _nse_ticker(ticker)
    cache_key = (nse_sym, interval, period)

    # Check cache
    if use_cache and cache_key in _cache:
        cached_at, cached_df = _cache[cache_key]
        ttl = _CACHE_TTL_SECONDS.get(interval, 60)
        if (datetime.now(timezone.utc) - cached_at).total_seconds() < ttl:
            logger.debug(f"Cache hit for {cache_key}")
            return cached_df.copy()

    # Fetch from yfinance
    logger.info(f"Fetching {nse_sym} interval={interval} period={period}")
    try:
        yf_ticker = yf.Ticker(nse_sym)
        df = yf_ticker.history(period=period, interval=interval)

        if df.empty:
            logger.warning(f"No data returned for {nse_sym}")
            return pd.DataFrame()

        df = _clean_columns(df)

        # Keep only OHLCV columns
        required = ["open", "high", "low", "close", "volume"]
        if "adj close" in df.columns:
            required.append("adj close")
        available = [c for c in required if c in df.columns]
        df = df[available].copy()

        # Drop rows with NaN in critical columns
        df.dropna(subset=["open", "high", "low", "close"], inplace=True)

        # Cache
        _cache[cache_key] = (datetime.now(timezone.utc), df.copy())

        return df

    except Exception as e:
        logger.error(f"Error fetching data for {nse_sym}: {e}")
        return pd.DataFrame()


def search_tickers(query: str, max_results: int = 10) -> list[dict]:
    """
    Search for NSE tickers matching a query string.

    Returns a list of dicts: [{"symbol": "RELIANCE.NS", "name": "Reliance Industries..."}]
    """
    try:
        results = []
        # yfinance doesn't have a native search, so we use the Ticker info
        # For a proper search we'd query a ticker list, but for V1 we do a simple lookup
        test_ticker = _nse_ticker(query)
        yf_t = yf.Ticker(test_ticker)
        info = yf_t.info
        if info and info.get("symbol"):
            results.append({
                "symbol": info.get("symbol", test_ticker),
                "name": info.get("longName", info.get("shortName", query)),
                "exchange": info.get("exchange", "NSE"),
                "sector": info.get("sector", ""),
            })
        return results[:max_results]
    except Exception as e:
        logger.error(f"Ticker search error for '{query}': {e}")
        return []


def get_current_price(ticker: str) -> Optional[float]:
    """Get the latest available price for an NSE ticker."""
    try:
        nse_sym = _nse_ticker(ticker)
        yf_t = yf.Ticker(nse_sym)
        data = yf_t.history(period="1d", interval="1m")
        if data.empty:
            return None
        data = _clean_columns(data)
        return float(data["close"].iloc[-1])
    except Exception as e:
        logger.error(f"Error getting current price for {ticker}: {e}")
        return None


def clear_cache():
    """Clear the entire in-memory data cache."""
    _cache.clear()
    logger.info("Data cache cleared")
