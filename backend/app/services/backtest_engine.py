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
    sell_threshold = 3

    def init(self):
        # Pre-calculated scores are already in the dataframe
        pass

    def next(self):
        buy_score = self.data.BUY_SCORE[-1]
        sell_score = self.data.SELL_SCORE[-1]

        if not self.position:
            if buy_score >= self.buy_threshold:
                self.buy()
        else:
            # If we hold a long position, check if we should sell
            if sell_score >= self.sell_threshold:
                self.position.close()


def run_backtest(
    ticker: str, 
    period: str, 
    initial_capital: float, 
    buy_threshold: int, 
    sell_threshold: int
) -> Dict[str, Any]:
    """
    Run a historical backtest for a ticker using Long-Term indicator logic.
    """
    # 1. Fetch data
    df = fetch_ohlcv(ticker, interval="1wk", period=period, use_cache=False)
    if df.empty:
        raise ValueError(f"No data available for {ticker} over {period}")

    # 2. Calculate Indicators
    # calculate_indicators expects columns open, high, low, close, volume
    ind = calculate_indicators(df, mode="long_term", include_series=True)
    if ind is None or not ind.series:
        raise ValueError(f"Insufficient data to calculate indicators for {ticker}")

    series = ind.series
    
    # 3. Vectorize signals
    # Rename DataFrame to Backtesting.py expected format
    df_bt = df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume"
    }).copy()
    
    close = df_bt["Close"]
    
    # Initialize score columns
    df_bt["BUY_SCORE"] = 0
    df_bt["SELL_SCORE"] = 0
    
    # Ensure series are aligned with df_bt index
    ema_200 = series.get("ema_200")
    if ema_200 is not None:
        df_bt["BUY_SCORE"] += np.where(close > ema_200, 1, 0)
        df_bt["SELL_SCORE"] += np.where(close < ema_200, 1, 0)
        
    st_dir = series.get("supertrend_dir")
    if st_dir is not None:
        df_bt["BUY_SCORE"] += np.where(st_dir == 1, 1, 0)
        df_bt["SELL_SCORE"] += np.where(st_dir == -1, 1, 0)
        
    rsi = series.get("rsi")
    if rsi is not None:
        rsi_rising = rsi > rsi.shift(1)
        rsi_falling = rsi < rsi.shift(1)
        # Buy: 50 < RSI < 70, rising
        df_bt["BUY_SCORE"] += np.where((rsi > 50) & (rsi < 70) & rsi_rising, 1, 0)
        # Sell: RSI < 50, falling
        df_bt["SELL_SCORE"] += np.where((rsi < 50) & rsi_falling, 1, 0)
        
    macd_line = series.get("macd_line")
    macd_signal = series.get("macd_signal")
    macd_hist = series.get("macd_hist")
    
    if macd_line is not None and macd_signal is not None and macd_hist is not None:
        df_bt["BUY_SCORE"] += np.where((macd_line > macd_signal) & (macd_hist > 0), 1, 0)
        df_bt["SELL_SCORE"] += np.where((macd_line < macd_signal) & (macd_hist < 0), 1, 0)

    # 4. Run Backtest
    # Delivery commission estimation: STT(0.1%) + Exchange(0.003%) + Stamp(0.015%) = ~0.12%
    # We apply 0.12% (0.0012) to closely match real NSE delivery charges.
    bt = Backtest(
        df_bt, 
        TradeSentinelStrategy, 
        cash=initial_capital, 
        commission=0.0012, 
        exclusive_orders=True,
        trade_on_close=True
    )
    
    stats = bt.run(buy_threshold=buy_threshold, sell_threshold=sell_threshold)
    trades = stats["_trades"]
    
    # 5. Serialize results
    # Drop internal data series from stats to keep JSON clean
    stats_dict = {
        "start": str(stats.get("Start", "")),
        "end": str(stats.get("End", "")),
        "duration": str(stats.get("Duration", "")),
        "return_pct": round(stats.get("Return [%]", 0), 2),
        "buy_hold_return_pct": round(stats.get("Buy & Hold Return [%]", 0), 2),
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

    return {
        "stats": stats_dict,
        "trades": trades_list
    }
