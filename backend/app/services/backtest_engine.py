import logging
import pandas as pd
import numpy as np
from typing import Dict, Any

from backtesting import Backtest, Strategy
from app.services.data_fetcher import fetch_ohlcv
from app.services.indicators import calculate_indicators

logger = logging.getLogger(__name__)

class TradeSentinelStrategy(Strategy):
    buy_threshold = 3

    def init(self):
        self.peak_price_since_entry = 0.0

    def next(self):
        buy_score = self.data.BUY_SCORE[-1]
        current_close = self.data.Close[-1]
        
        # safely access indicators, defaulting to NaN if not calculated yet
        weekly_sma_200 = self.data.weekly_sma_200[-1] if 'weekly_sma_200' in self.data.df.columns else np.nan

        if not self.position:
            if buy_score >= self.buy_threshold:
                self.buy()
                self.peak_price_since_entry = current_close
        else:
            # We are in a position, update peak price
            if current_close > self.peak_price_since_entry:
                self.peak_price_since_entry = current_close
                
            # Exit Conditions
            # Condition B: Price drops 20% from peak since entry
            cond_b = current_close <= self.peak_price_since_entry * 0.80
            # Condition C: Price closes > 10% below the 200-W SMA
            cond_c = not pd.isna(weekly_sma_200) and current_close < (weekly_sma_200 * 0.90)
            
            if cond_b or cond_c:
                self.position.close()
                self.peak_price_since_entry = 0.0


def run_backtest(
    ticker: str, 
    period: str, 
    initial_capital: float, 
    buy_threshold: int, 
    sell_threshold: int
) -> Dict[str, Any]:
    """
    Run a historical backtest for a ticker using Long-Term indicator logic.
    (sell_threshold is now ignored, trend-following exits are hardcoded)
    """
    # 1. Fetch data
    df = fetch_ohlcv(ticker, interval="1wk", period=period, use_cache=False)
    if df.empty:
        raise ValueError(f"No data available for {ticker} over {period}")

    # 2. Calculate Indicators
    ind = calculate_indicators(df, mode="long_term", include_series=True)
    if ind is None or not ind.series:
        raise ValueError(f"Insufficient data to calculate indicators for {ticker}")

    series = ind.series
    
    # 3. Vectorize signals
    df_bt = df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume"
    }).copy()
    
    close = df_bt["Close"]
    df_bt["BUY_SCORE"] = 0
    
    # Store indicators in df_bt for the strategy to access
    sma_200 = series.get("weekly_sma_200")
    if sma_200 is not None:
        sma_200 = sma_200.reindex(close.index)
        df_bt["weekly_sma_200"] = sma_200
        # Buy: 200-W SMA Proximity (within +3% to -5%)
        df_bt["BUY_SCORE"] += ((close <= sma_200 * 1.03) & (close >= sma_200 * 0.95)).astype(int)
    else:
        df_bt["weekly_sma_200"] = np.nan
        
    ema_50 = series.get("weekly_ema_50")
    if ema_50 is not None:
        df_bt["weekly_ema_50"] = ema_50.reindex(close.index)
    else:
        df_bt["weekly_ema_50"] = np.nan

    rsi = series.get("rsi")
    if rsi is not None:
        rsi = rsi.reindex(close.index)
        # Buy: RSI <= 42
        df_bt["BUY_SCORE"] += (rsi <= 42).astype(int)
        
    bb_lower = series.get("weekly_bb_lower")
    if bb_lower is not None:
        bb_lower = bb_lower.reindex(close.index)
        # Buy: Near lower BB
        df_bt["BUY_SCORE"] += (close <= bb_lower * 1.02).astype(int)
        
    macd_line = series.get("macd_line")
    macd_signal = series.get("macd_signal")
    macd_hist = series.get("macd_histogram") 
    
    if macd_line is not None and macd_signal is not None and macd_hist is not None:
        macd_line = macd_line.reindex(close.index)
        macd_signal = macd_signal.reindex(close.index)
        macd_hist = macd_hist.reindex(close.index)
        
        macd_bullish_cross = macd_line > macd_signal
        macd_hist_prev = macd_hist.shift(1)
        hist_rising_from_neg = (macd_hist > macd_hist_prev) & (macd_hist_prev < 0)
        
        df_bt["BUY_SCORE"] += (macd_bullish_cross | hist_rising_from_neg).astype(int)

    # 4. Run Backtest
    bt = Backtest(
        df_bt, 
        TradeSentinelStrategy, 
        cash=initial_capital, 
        commission=0.0012, 
        exclusive_orders=True,
        trade_on_close=True
    )
    
    # We pass buy_threshold, but sell_threshold is no longer used by the strategy
    stats = bt.run(buy_threshold=buy_threshold)
    trades = stats["_trades"]
    
    years = (df.index[-1] - df.index[0]).days / 365.25
    strategy_return = stats.get("Return [%]", 0)
    bnh_return = stats.get("Buy & Hold Return [%]", 0)
    
    strat_cagr = ((1 + strategy_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
    bnh_cagr = ((1 + bnh_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
    exposure = stats.get("Exposure Time [%]", 0)
    
    # 5. Serialize results
    stats_dict = {
        "start": str(stats.get("Start", "")),
        "end": str(stats.get("End", "")),
        "duration": str(stats.get("Duration", "")),
        "return_pct": round(strategy_return, 2),
        "buy_hold_return_pct": round(bnh_return, 2),
        "strategy_cagr_pct": round(strat_cagr, 2),
        "buy_hold_cagr_pct": round(bnh_cagr, 2),
        "cash_drag_pct": round(100 - exposure, 2),
        "max_drawdown_pct": round(stats.get("Max. Drawdown [%]", 0), 2),
        "win_rate_pct": round(stats.get("Win Rate [%]", 0), 2),
        "total_trades": int(stats.get("# Trades", 0)),
        "expectancy_pct": round(stats.get("Expectancy [%]", 0) if not pd.isna(stats.get("Expectancy [%]", 0)) else 0, 2),
        "profit_factor": round(stats.get("Profit Factor", 0) if not pd.isna(stats.get("Profit Factor", 0)) else 0, 2),
        "sharpe_ratio": round(stats.get("Sharpe Ratio", 0) if not pd.isna(stats.get("Sharpe Ratio", 0)) else 0, 2),
        "sortino_ratio": round(stats.get("Sortino Ratio", 0) if not pd.isna(stats.get("Sortino Ratio", 0)) else 0, 2),
    }

    trades_list = []
    if not trades.empty:
        for idx, row in trades.iterrows():
            trades_list.append({
                "size": int(row.get("Size", 0)),
                "entry_price": float(row.get("EntryPrice", 0)),
                "exit_price": float(row.get("ExitPrice", 0)),
                "entry_time": str(row.get("EntryTime", "")),
                "exit_time": str(row.get("ExitTime", "")),
                "pnl": float(row.get("PnL", 0)),
                "return_pct": float(row.get("ReturnPct", 0) * 100),
                "duration": str(row.get("Duration", ""))
            })

    # Also append currently open trades
    strategy_instance = stats.get("_strategy")
    if strategy_instance and hasattr(strategy_instance, "trades"):
        for t in strategy_instance.trades:
            trades_list.append({
                "size": int(t.size),
                "entry_price": float(t.entry_price),
                "exit_price": float(close.iloc[-1]), 
                "entry_time": str(df_bt.index[t.entry_bar]),
                "exit_time": "Open",
                "pnl": float(t.pl),
                "return_pct": float(t.pl_pct * 100),
                "duration": "Ongoing"
            })
            
    trades_list.reverse()

    return {
        "stats": stats_dict,
        "trades": trades_list
    }
