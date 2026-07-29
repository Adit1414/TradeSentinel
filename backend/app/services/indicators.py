"""Technical indicator calculations using pandas-ta.

Computes VWAP, 200 EMA, Supertrend, RSI, and MACD on OHLCV DataFrames.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import pandas_ta_classic as ta

logger = logging.getLogger(__name__)


@dataclass
class IndicatorResult:
    """Container for calculated indicator values at the latest candle."""

    price: float = 0.0

    # VWAP (intraday only)
    vwap: Optional[float] = None

    # EMA 200 (long-term only)
    ema_200: Optional[float] = None

    # Supertrend
    supertrend_value: float = 0.0
    supertrend_direction: int = 0  # 1 = bullish (green), -1 = bearish (red)

    # RSI
    rsi: float = 0.0
    rsi_prev: float = 0.0
    rsi_rising: bool = False

    # MACD
    macd_line: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    macd_line_prev: float = 0.0
    macd_signal_prev: float = 0.0
    macd_crossover: str = "none"  # "bullish" | "bearish" | "none"

    # Full series for charting (populated when requested)
    series: dict = field(default_factory=dict)


def calculate_indicators(
    df: pd.DataFrame,
    mode: str = "intraday",
    include_series: bool = False,
    supertrend_length: int = 7,
    supertrend_multiplier: float = 3.0,
) -> Optional[IndicatorResult]:
    """
    Calculate all 4 technical indicators on the given OHLCV DataFrame.

    Args:
        df: DataFrame with columns: open, high, low, close, volume. DatetimeIndex.
        mode: "intraday", "short_selling", or "long_term".
        include_series: If True, attach full indicator series for charting.
        supertrend_length: Supertrend ATR period.
        supertrend_multiplier: Supertrend multiplier.

    Returns:
        IndicatorResult with latest values, or None if insufficient data.
    """
    if df is None or df.empty or len(df) < 30:
        logger.warning("Insufficient data for indicator calculation")
        return None

    result = IndicatorResult()

    # Ensure we have the required columns
    required = ["open", "high", "low", "close"]
    if not all(c in df.columns for c in required):
        logger.error(f"Missing required columns. Have: {list(df.columns)}")
        return None

    try:
        # ── Current Price ──────────────────────────────────────────────
        result.price = float(df["close"].iloc[-1])

        # ── VWAP (intraday modes only) ─────────────────────────────────
        if mode in ("intraday", "short_selling"):
            if "volume" in df.columns:
                vwap_series = ta.vwap(
                    high=df["high"], low=df["low"], close=df["close"],
                    volume=df["volume"]
                )
                if vwap_series is not None and not vwap_series.empty:
                    result.vwap = float(vwap_series.iloc[-1])
                    if include_series:
                        result.series["vwap"] = vwap_series.dropna()

        # ── 200 EMA (long-term mode only) ──────────────────────────────
        if mode == "long_term":
            ema_series = ta.ema(close=df["close"], length=200)
            if ema_series is not None and not ema_series.empty:
                result.ema_200 = float(ema_series.iloc[-1]) if not pd.isna(ema_series.iloc[-1]) else None
                if include_series:
                    result.series["ema_200"] = ema_series.dropna()

        # ── Supertrend ─────────────────────────────────────────────────
        st_df = ta.supertrend(
            high=df["high"], low=df["low"], close=df["close"],
            length=supertrend_length, multiplier=supertrend_multiplier,
        )
        if st_df is not None and not st_df.empty:
            # pandas-ta returns columns like: SUPERT_7_3.0, SUPERTd_7_3.0, etc.
            st_cols = st_df.columns.tolist()
            supert_col = [c for c in st_cols if c.startswith("SUPERT_") and not c.startswith("SUPERTd") and not c.startswith("SUPERTl") and not c.startswith("SUPERTs")][0]
            supertd_col = [c for c in st_cols if c.startswith("SUPERTd_")][0]

            result.supertrend_value = float(st_df[supert_col].iloc[-1])
            result.supertrend_direction = int(st_df[supertd_col].iloc[-1])

            if include_series:
                # Build supertrend series with direction info
                result.series["supertrend"] = st_df[supert_col].dropna()
                result.series["supertrend_direction"] = st_df[supertd_col].dropna()

        # ── RSI (14) ───────────────────────────────────────────────────
        rsi_series = ta.rsi(close=df["close"], length=14)
        if rsi_series is not None and len(rsi_series.dropna()) >= 2:
            result.rsi = float(rsi_series.iloc[-1])
            result.rsi_prev = float(rsi_series.iloc[-2])
            result.rsi_rising = result.rsi > result.rsi_prev

            if include_series:
                result.series["rsi"] = rsi_series.dropna()

        # ── MACD (12, 26, 9) ──────────────────────────────────────────
        macd_df = ta.macd(close=df["close"], fast=12, slow=26, signal=9)
        if macd_df is not None and not macd_df.empty:
            macd_cols = macd_df.columns.tolist()
            # Columns: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
            macd_col = [c for c in macd_cols if c.startswith("MACD_")][0]
            macdh_col = [c for c in macd_cols if c.startswith("MACDh_")][0]
            macds_col = [c for c in macd_cols if c.startswith("MACDs_")][0]

            macd_clean = macd_df.dropna()
            if len(macd_clean) >= 2:
                result.macd_line = float(macd_clean[macd_col].iloc[-1])
                result.macd_signal = float(macd_clean[macds_col].iloc[-1])
                result.macd_histogram = float(macd_clean[macdh_col].iloc[-1])
                result.macd_line_prev = float(macd_clean[macd_col].iloc[-2])
                result.macd_signal_prev = float(macd_clean[macds_col].iloc[-2])

                # Detect crossover
                if (result.macd_line > result.macd_signal and
                        result.macd_line_prev <= result.macd_signal_prev):
                    result.macd_crossover = "bullish"
                elif (result.macd_line < result.macd_signal and
                      result.macd_line_prev >= result.macd_signal_prev):
                    result.macd_crossover = "bearish"
                else:
                    result.macd_crossover = "none"

                if include_series:
                    result.series["macd_line"] = macd_df[macd_col].dropna()
                    result.series["macd_signal"] = macd_df[macds_col].dropna()
                    result.series["macd_histogram"] = macd_df[macdh_col].dropna()

        return result

    except Exception as e:
        logger.error(f"Error calculating indicators: {e}", exc_info=True)
        return None


def get_chart_data(df: pd.DataFrame, mode: str = "intraday") -> dict:
    """
    Build chart-ready data including OHLCV candles and all indicator series.

    Returns a dict suitable for the frontend charting component.
    """
    if df is None or df.empty:
        return {"candles": [], "indicators": {}}

    result = calculate_indicators(df, mode=mode, include_series=True)

    # Build candle data in TradingView Lightweight Charts format
    candles = []
    for idx, row in df.iterrows():
        ts = int(idx.timestamp()) if hasattr(idx, "timestamp") else 0
        candles.append({
            "time": ts,
            "open": round(float(row["open"]), 2),
            "high": round(float(row["high"]), 2),
            "low": round(float(row["low"]), 2),
            "close": round(float(row["close"]), 2),
        })

    # Build indicator time-value pairs
    indicators = {}
    if result:
        # VWAP / EMA overlay
        overlay_key = "vwap" if mode in ("intraday", "short_selling") else "ema_200"
        overlay_series = result.series.get(overlay_key)
        if overlay_series is not None:
            indicators[overlay_key] = [
                {"time": int(idx.timestamp()) if hasattr(idx, "timestamp") else 0, "value": round(float(v), 2)}
                for idx, v in overlay_series.items()
            ]

        # Supertrend overlay
        st_series = result.series.get("supertrend")
        st_dir_series = result.series.get("supertrend_direction")
        if st_series is not None and st_dir_series is not None:
            indicators["supertrend"] = [
                {
                    "time": int(idx.timestamp()) if hasattr(idx, "timestamp") else 0,
                    "value": round(float(v), 2),
                    "color": "#00e676" if (idx in st_dir_series and st_dir_series[idx] == 1) else "#ff1744",
                }
                for idx, v in st_series.items()
            ]

        # RSI
        rsi_series = result.series.get("rsi")
        if rsi_series is not None:
            indicators["rsi"] = [
                {"time": int(idx.timestamp()) if hasattr(idx, "timestamp") else 0, "value": round(float(v), 2)}
                for idx, v in rsi_series.items()
            ]

        # MACD
        for key in ("macd_line", "macd_signal", "macd_histogram"):
            series = result.series.get(key)
            if series is not None:
                indicators[key] = [
                    {"time": int(idx.timestamp()) if hasattr(idx, "timestamp") else 0, "value": round(float(v), 4)}
                    for idx, v in series.items()
                ]

    return {
        "candles": candles,
        "indicators": indicators,
        "latest": {
            "price": result.price if result else 0,
            "vwap": result.vwap,
            "ema_200": result.ema_200,
            "supertrend_value": result.supertrend_value if result else 0,
            "supertrend_direction": result.supertrend_direction if result else 0,
            "rsi": result.rsi if result else 0,
            "rsi_rising": result.rsi_rising if result else False,
            "macd_line": result.macd_line if result else 0,
            "macd_signal": result.macd_signal if result else 0,
            "macd_histogram": result.macd_histogram if result else 0,
            "macd_crossover": result.macd_crossover if result else "none",
        } if result else {},
    }
