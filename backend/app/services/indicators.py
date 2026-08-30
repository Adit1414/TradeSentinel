"""Technical indicator calculations using pandas-ta.

Intraday / Short-Selling modes (5-min): VWAP, Supertrend, RSI-14, MACD 12/26/9.
Long-Term mode (weekly): 200-Week SMA, RSI-14, MACD 12/26/9, Bollinger Bands 20/2.
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

    # VWAP (intraday / short_selling only)
    vwap: Optional[float] = None

    # EMA 200 (legacy — kept for backward-compat; not used by long_term mode)
    ema_200: Optional[float] = None

    # Supertrend (intraday / short_selling only)
    supertrend_value: float = 0.0
    supertrend_direction: int = 0  # 1 = bullish (green), -1 = bearish (red)

    # RSI (all modes — long_term uses 14-period weekly RSI)
    rsi: float = 0.0
    rsi_prev: float = 0.0
    rsi_rising: bool = False

    # MACD (all modes — long_term uses weekly MACD 12/26/9)
    macd_line: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    macd_histogram_prev: float = 0.0  # for detecting histogram direction
    macd_line_prev: float = 0.0
    macd_signal_prev: float = 0.0
    macd_crossover: str = "none"  # "bullish" | "bearish" | "none"

    # ── Weekly indicators (long_term mode only) ────────────────────────────────
    # 200-Week Simple Moving Average
    weekly_sma_200: Optional[float] = None
    weekly_ema_50: Optional[float] = None
    weekly_52w_high: Optional[float] = None

    # Weekly Bollinger Bands (20, 2)
    weekly_bb_lower: Optional[float] = None
    weekly_bb_mid: Optional[float] = None
    weekly_bb_upper: Optional[float] = None

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
    Calculate technical indicators on the given OHLCV DataFrame.

    Args:
        df: DataFrame with columns: open, high, low, close, volume. DatetimeIndex.
        mode: "intraday", "short_selling", or "long_term".
              long_term uses weekly candles (SMA-200, RSI-14, MACD 12/26/9, BBands 20/2).
        include_series: If True, attach full indicator series for charting.
        supertrend_length: Supertrend ATR period (intraday/short_selling only).
        supertrend_multiplier: Supertrend multiplier (intraday/short_selling only).

    Returns:
        IndicatorResult with latest values, or None if insufficient data.
    """
    # Long-term needs 200+ candles for the weekly SMA-200
    min_candles = 200 if mode == "long_term" else 30
    if df is None or df.empty or len(df) < min_candles:
        logger.warning(
            f"Insufficient data for {mode} indicator calculation "
            f"(need {min_candles}, got {len(df) if df is not None else 0})"
        )
        return None

    result = IndicatorResult()

    # Ensure we have the required columns
    required = ["open", "high", "low", "close"]
    if not all(c in df.columns for c in required):
        logger.error(f"Missing required columns. Have: {list(df.columns)}")
        return None

    try:
        close_col = "adj close" if "adj close" in df.columns else "close"

        # ── Current Price ──────────────────────────────────────────────
        result.price = float(df[close_col].iloc[-1])

        # ══════════════════════════════════════════════════════════════
        # LONG-TERM MODE — Weekly "Buy-the-Dip" Macro Indicator Pipeline
        # Indicators: 200-W SMA, RSI-14 (weekly), MACD 12/26/9 (weekly),
        #             Bollinger Bands 20/2 (weekly)
        # ══════════════════════════════════════════════════════════════
        if mode == "long_term":
            # ── A. 200-Week Simple Moving Average & 50-Week EMA ────────
            sma200_series = ta.sma(close=df[close_col], length=200)
            ema50_series = ta.ema(close=df[close_col], length=50)
            
            if sma200_series is not None and not sma200_series.empty:
                latest_sma200 = sma200_series.iloc[-1]
                result.weekly_sma_200 = (
                    float(latest_sma200) if not pd.isna(latest_sma200) else None
                )
                if include_series:
                    result.series["weekly_sma_200"] = sma200_series.dropna()
                    
            if ema50_series is not None and not ema50_series.empty:
                latest_ema50 = ema50_series.iloc[-1]
                result.weekly_ema_50 = float(latest_ema50) if not pd.isna(latest_ema50) else None
                result.series["weekly_ema_50"] = ema50_series.dropna()

            # 52-Week High
            high52_series = df[close_col].rolling(window=52, min_periods=1).max()
            if not high52_series.empty:
                latest_high52 = high52_series.iloc[-1]
                result.weekly_52w_high = float(latest_high52) if not pd.isna(latest_high52) else None
                result.series["weekly_52w_high"] = high52_series

            # ── B. Weekly RSI (14) ────────────────────────────────────
            rsi_series = ta.rsi(close=df[close_col], length=14)
            if rsi_series is not None and len(rsi_series.dropna()) >= 2:
                result.rsi = float(rsi_series.iloc[-1])
                result.rsi_prev = float(rsi_series.iloc[-2])
                result.rsi_rising = result.rsi > result.rsi_prev
                if include_series:
                    result.series["rsi"] = rsi_series.dropna()

            # ── C. Weekly MACD (12, 26, 9) ───────────────────────────
            macd_df = ta.macd(close=df[close_col], fast=12, slow=26, signal=9)
            if macd_df is not None and not macd_df.empty:
                macd_cols = macd_df.columns.tolist()
                macd_col  = [c for c in macd_cols if c.startswith("MACD_")][0]
                macdh_col = [c for c in macd_cols if c.startswith("MACDh_")][0]
                macds_col = [c for c in macd_cols if c.startswith("MACDs_")][0]

                macd_clean = macd_df.dropna()
                if len(macd_clean) >= 2:
                    result.macd_line          = float(macd_clean[macd_col].iloc[-1])
                    result.macd_signal        = float(macd_clean[macds_col].iloc[-1])
                    result.macd_histogram     = float(macd_clean[macdh_col].iloc[-1])
                    result.macd_histogram_prev = float(macd_clean[macdh_col].iloc[-2])
                    result.macd_line_prev     = float(macd_clean[macd_col].iloc[-2])
                    result.macd_signal_prev   = float(macd_clean[macds_col].iloc[-2])

                    if (result.macd_line > result.macd_signal and
                            result.macd_line_prev <= result.macd_signal_prev):
                        result.macd_crossover = "bullish"
                    elif (result.macd_line < result.macd_signal and
                          result.macd_line_prev >= result.macd_signal_prev):
                        result.macd_crossover = "bearish"
                    else:
                        result.macd_crossover = "none"

                    if include_series:
                        result.series["macd_line"]      = macd_df[macd_col].dropna()
                        result.series["macd_signal"]    = macd_df[macds_col].dropna()
                        result.series["macd_histogram"] = macd_df[macdh_col].dropna()

            # ── D. Weekly Bollinger Bands (20, 2) ────────────────────
            bb_df = ta.bbands(close=df[close_col], length=20, std=2)
            if bb_df is not None and not bb_df.empty:
                bb_cols = bb_df.columns.tolist()
                # pandas-ta names: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
                bbl_col = [c for c in bb_cols if c.startswith("BBL_")]
                bbm_col = [c for c in bb_cols if c.startswith("BBM_")]
                bbu_col = [c for c in bb_cols if c.startswith("BBU_")]
                if bbl_col and bbm_col and bbu_col:
                    bbl_val = bb_df[bbl_col[0]].iloc[-1]
                    bbm_val = bb_df[bbm_col[0]].iloc[-1]
                    bbu_val = bb_df[bbu_col[0]].iloc[-1]
                    result.weekly_bb_lower = float(bbl_val) if not pd.isna(bbl_val) else None
                    result.weekly_bb_mid   = float(bbm_val) if not pd.isna(bbm_val) else None
                    result.weekly_bb_upper = float(bbu_val) if not pd.isna(bbu_val) else None
                    if include_series:
                        result.series["weekly_bb_lower"] = bb_df[bbl_col[0]].dropna()
                        result.series["weekly_bb_mid"]   = bb_df[bbm_col[0]].dropna()
                        result.series["weekly_bb_upper"] = bb_df[bbu_col[0]].dropna()

            return result

        # ══════════════════════════════════════════════════════════════
        # INTRADAY / SHORT-SELLING MODE — 5-minute timeframe pipeline
        # Indicators: VWAP, Supertrend, RSI-14, MACD 12/26/9
        # ══════════════════════════════════════════════════════════════

        # ── VWAP (intraday modes only) ─────────────────────────────────
        if mode in ("intraday", "short_selling"):
            if "volume" in df.columns:
                vwap_series = ta.vwap(
                    high=df["high"], low=df["low"], close=df[close_col],
                    volume=df["volume"]
                )
                if vwap_series is not None and not vwap_series.empty:
                    result.vwap = float(vwap_series.iloc[-1])
                    if include_series:
                        result.series["vwap"] = vwap_series.dropna()

        # ── Supertrend ─────────────────────────────────────────────────
        st_df = ta.supertrend(
            high=df["high"], low=df["low"], close=df[close_col],
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
        rsi_series = ta.rsi(close=df[close_col], length=14)
        if rsi_series is not None and len(rsi_series.dropna()) >= 2:
            result.rsi = float(rsi_series.iloc[-1])
            result.rsi_prev = float(rsi_series.iloc[-2])
            result.rsi_rising = result.rsi > result.rsi_prev

            if include_series:
                result.series["rsi"] = rsi_series.dropna()

        # ── MACD (12, 26, 9) ──────────────────────────────────────────
        macd_df = ta.macd(close=df[close_col], fast=12, slow=26, signal=9)
        if macd_df is not None and not macd_df.empty:
            macd_cols = macd_df.columns.tolist()
            # Columns: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
            macd_col  = [c for c in macd_cols if c.startswith("MACD_")][0]
            macdh_col = [c for c in macd_cols if c.startswith("MACDh_")][0]
            macds_col = [c for c in macd_cols if c.startswith("MACDs_")][0]

            macd_clean = macd_df.dropna()
            if len(macd_clean) >= 2:
                result.macd_line          = float(macd_clean[macd_col].iloc[-1])
                result.macd_signal        = float(macd_clean[macds_col].iloc[-1])
                result.macd_histogram     = float(macd_clean[macdh_col].iloc[-1])
                result.macd_histogram_prev = float(macd_clean[macdh_col].iloc[-2])
                result.macd_line_prev     = float(macd_clean[macd_col].iloc[-2])
                result.macd_signal_prev   = float(macd_clean[macds_col].iloc[-2])

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
                    result.series["macd_line"]      = macd_df[macd_col].dropna()
                    result.series["macd_signal"]    = macd_df[macds_col].dropna()
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
        # Offset the timestamp by +5:30 (19800 seconds) to force Lightweight Charts 
        # to render it as IST time on the x-axis.
        ts = (int(idx.timestamp()) + 19800) if hasattr(idx, "timestamp") else 0
        candles.append({
            "time": ts,
            "open": round(float(row["open"]), 2),
            "high": round(float(row["high"]), 2),
            "low": round(float(row["low"]), 2),
            "close": round(float(row["adj close"] if "adj close" in row else row["close"]), 2),
        })

    # Build indicator time-value pairs
    indicators = {}
    if result:
        # VWAP (intraday) / weekly SMA-200 (long_term) overlay
        if mode in ("intraday", "short_selling"):
            overlay_series = result.series.get("vwap")
            if overlay_series is not None:
                indicators["vwap"] = [
                    {"time": (int(idx.timestamp()) + 19800) if hasattr(idx, "timestamp") else 0, "value": round(float(v), 2)}
                    for idx, v in overlay_series.items()
                ]
        else:  # long_term — weekly SMA-200 and BB bands as overlays
            for overlay_key in ("weekly_sma_200", "weekly_bb_lower", "weekly_bb_mid", "weekly_bb_upper"):
                overlay_series = result.series.get(overlay_key)
                if overlay_series is not None:
                    indicators[overlay_key] = [
                        {"time": (int(idx.timestamp()) + 19800) if hasattr(idx, "timestamp") else 0, "value": round(float(v), 2)}
                        for idx, v in overlay_series.items()
                    ]

        # Supertrend overlay
        st_series = result.series.get("supertrend")
        st_dir_series = result.series.get("supertrend_direction")
        if st_series is not None and st_dir_series is not None:
            indicators["supertrend"] = [
                {
                    "time": (int(idx.timestamp()) + 19800) if hasattr(idx, "timestamp") else 0,
                    "value": round(float(v), 2),
                    "color": "#00e676" if (idx in st_dir_series and st_dir_series[idx] == 1) else "#ff1744",
                }
                for idx, v in st_series.items()
            ]

        # RSI
        rsi_series = result.series.get("rsi")
        if rsi_series is not None:
            indicators["rsi"] = [
                {"time": (int(idx.timestamp()) + 19800) if hasattr(idx, "timestamp") else 0, "value": round(float(v), 2)}
                for idx, v in rsi_series.items()
            ]

        # MACD
        for key in ("macd_line", "macd_signal", "macd_histogram"):
            series = result.series.get(key)
            if series is not None:
                indicators[key] = [
                    {"time": (int(idx.timestamp()) + 19800) if hasattr(idx, "timestamp") else 0, "value": round(float(v), 4)}
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
            # Weekly long-term indicators
            "weekly_sma_200": result.weekly_sma_200 if result else None,
            "weekly_bb_lower": result.weekly_bb_lower if result else None,
            "weekly_bb_mid": result.weekly_bb_mid if result else None,
            "weekly_bb_upper": result.weekly_bb_upper if result else None,
        } if result else {},
    }
