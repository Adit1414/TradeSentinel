import logging
import pandas as pd
import numpy as np
from typing import Dict, Any

from backtesting import Backtest, Strategy
from app.services.data_fetcher import fetch_ohlcv
from app.services.indicators import calculate_indicators

logger = logging.getLogger(__name__)

class TradeSentinelStrategy(Strategy):
    entry_strategy = 1
    exit_strategy = 2

    def init(self):
        self.peak_price_since_entry = 0.0

    def next(self):
        buy_score = self.data.BUY_SCORE[-1]
        current_close = self.data.Close[-1]
        
        # safely access indicators, defaulting to NaN if not calculated yet
        weekly_sma_200 = self.data.weekly_sma_200[-1] if 'weekly_sma_200' in self.data.df.columns else np.nan
        weekly_rsi = self.data.rsi[-1] if 'rsi' in self.data.df.columns else np.nan
        weekly_bb_upper = self.data.weekly_bb_upper[-1] if 'weekly_bb_upper' in self.data.df.columns else np.nan
        macd_line = self.data.macd_line[-1] if 'macd_line' in self.data.df.columns else np.nan
        macd_signal = self.data.macd_signal[-1] if 'macd_signal' in self.data.df.columns else np.nan
        weekly_ema_10 = self.data.weekly_ema_10[-1] if 'weekly_ema_10' in self.data.df.columns else np.nan
        weekly_ema_40 = self.data.weekly_ema_40[-1] if 'weekly_ema_40' in self.data.df.columns else np.nan
        weekly_sma_40 = self.data.weekly_sma_40[-1] if 'weekly_sma_40' in self.data.df.columns else np.nan
        weekly_52w_high_prev = self.data.weekly_52w_high[-2] if 'weekly_52w_high' in self.data.df.columns and len(self.data.weekly_52w_high) > 1 else np.nan
        weekly_20w_low_prev = self.data.weekly_20w_low[-2] if 'weekly_20w_low' in self.data.df.columns and len(self.data.weekly_20w_low) > 1 else np.nan
        weekly_supertrend_bullish = self.data.weekly_supertrend_bullish[-1] if 'weekly_supertrend_bullish' in self.data.df.columns else False
        current_low = self.data.Low[-1]

        if not self.position:
            if self.entry_strategy == 1:
                # Option 1: Deep Value (3-of-4 Indicators)
                if buy_score >= 3:
                    self.buy()
                    self.peak_price_since_entry = current_close
            elif self.entry_strategy == 2:
                # Option 2: Macro Trend Follower (10W/40W EMA Cross)
                if not pd.isna(weekly_ema_10) and not pd.isna(weekly_ema_40):
                    if weekly_ema_10 > weekly_ema_40:
                        self.buy()
                        self.peak_price_since_entry = current_close
            elif self.entry_strategy == 3:
                # Option 3: 52-Week High Breakout (Stage 2)
                if not pd.isna(weekly_52w_high_prev) and not pd.isna(weekly_ema_40):
                    if current_close >= weekly_52w_high_prev and current_close > weekly_ema_40:
                        self.buy()
                        self.peak_price_since_entry = current_close
            elif self.entry_strategy == 4:
                # Option 4: Weekly Trend Pullback (10W EMA Dip)
                if not pd.isna(weekly_ema_10) and not pd.isna(weekly_ema_40):
                    if weekly_ema_10 > weekly_ema_40 and current_low <= weekly_ema_10 * 1.01 and current_close > weekly_ema_10:
                        self.buy()
                        self.peak_price_since_entry = current_close
            elif self.entry_strategy == 5:
                # Option 5: Pure 40-Week SMA Trend (Zero-Lag)
                if not pd.isna(weekly_sma_40):
                    if current_close > weekly_sma_40:
                        self.buy()
                        self.peak_price_since_entry = current_close
        else:
            # We are in a position, update peak price
            if current_close > self.peak_price_since_entry:
                self.peak_price_since_entry = current_close
                
            # Evaluate exit based on exit_strategy
            exit_triggered = False
            
            if self.exit_strategy == 1:
                # Option 1: Pure Oscillators
                if (not pd.isna(weekly_rsi) and weekly_rsi >= 70) or \
                   (not pd.isna(weekly_bb_upper) and current_close >= weekly_bb_upper):
                    exit_triggered = True
                    
            elif self.exit_strategy == 2:
                # Option 2: Structural Breakdown
                cond_b = current_close <= self.peak_price_since_entry * 0.80
                cond_c = not pd.isna(weekly_sma_200) and current_close < (weekly_sma_200 * 0.90)
                if cond_b or cond_c:
                    exit_triggered = True
                    
            elif self.exit_strategy == 3:
                # Option 3: Macro Momentum Shift
                if not pd.isna(weekly_rsi) and not pd.isna(macd_line) and not pd.isna(macd_signal):
                    if weekly_rsi >= 70 and macd_line < macd_signal:
                        exit_triggered = True
                        
            elif self.exit_strategy == 4:
                # Option 4: Macro Trend Breakdown
                if not pd.isna(weekly_ema_10) and not pd.isna(weekly_ema_40):
                    if weekly_ema_10 < weekly_ema_40:
                        exit_triggered = True
                        
            elif self.exit_strategy == 5:
                # Option 5: Weekly Supertrend Flip (10, 3)
                if not weekly_supertrend_bullish:
                    exit_triggered = True
                    
            elif self.exit_strategy == 6:
                # Option 6: 20-Week Low Channel Breakdown
                if not pd.isna(weekly_20w_low_prev):
                    if current_close < weekly_20w_low_prev:
                        exit_triggered = True
                        
            elif self.exit_strategy == 7:
                # Option 7: 40-Week SMA Loss (Zero-Lag)
                if not pd.isna(weekly_sma_40):
                    if current_close < weekly_sma_40:
                        exit_triggered = True
            
            if exit_triggered:
                self.position.close()
                self.peak_price_since_entry = 0.0


def run_backtest(
    ticker: str, 
    period: str, 
    initial_capital: float, 
    sell_threshold: int,
    entry_strategy: int = 1,
    exit_strategy: int = 2
) -> Dict[str, Any]:
    """
    Run a historical backtest for a ticker using Long-Term indicator logic.
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
    close_col = "adj close" if "adj close" in df.columns else "close"
    df_bt = df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        close_col: "Close",
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
        
    sma_40 = series.get("weekly_sma_40")
    if sma_40 is not None:
        df_bt["weekly_sma_40"] = sma_40.reindex(close.index)
    else:
        df_bt["weekly_sma_40"] = np.nan
        
    ema_10 = series.get("weekly_ema_10")
    if ema_10 is not None:
        df_bt["weekly_ema_10"] = ema_10.reindex(close.index)
    else:
        df_bt["weekly_ema_10"] = np.nan
        
    ema_40 = series.get("weekly_ema_40")
    if ema_40 is not None:
        df_bt["weekly_ema_40"] = ema_40.reindex(close.index)
    else:
        df_bt["weekly_ema_40"] = np.nan

    rsi = series.get("rsi")
    if rsi is not None:
        rsi = rsi.reindex(close.index)
        # Buy: RSI <= 42
        df_bt["BUY_SCORE"] += (rsi <= 42).astype(int)
        df_bt["rsi"] = rsi
    else:
        df_bt["rsi"] = np.nan
        
    bb_lower = series.get("weekly_bb_lower")
    if bb_lower is not None:
        bb_lower = bb_lower.reindex(close.index)
        # Buy: Near lower BB
        df_bt["BUY_SCORE"] += (close <= bb_lower * 1.02).astype(int)
        
    bb_upper = series.get("weekly_bb_upper")
    if bb_upper is not None:
        df_bt["weekly_bb_upper"] = bb_upper.reindex(close.index)
    else:
        df_bt["weekly_bb_upper"] = np.nan
        
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
        df_bt["macd_line"] = macd_line
        df_bt["macd_signal"] = macd_signal
    else:
        df_bt["macd_line"] = np.nan
        df_bt["macd_signal"] = np.nan

    weekly_52w_high = series.get("weekly_52w_high")
    if weekly_52w_high is not None:
        df_bt["weekly_52w_high"] = weekly_52w_high.reindex(close.index)
    else:
        df_bt["weekly_52w_high"] = np.nan

    weekly_20w_low = series.get("weekly_20w_low")
    if weekly_20w_low is not None:
        df_bt["weekly_20w_low"] = weekly_20w_low.reindex(close.index)
    else:
        df_bt["weekly_20w_low"] = np.nan

    weekly_supertrend_bullish = series.get("weekly_supertrend_bullish")
    if weekly_supertrend_bullish is not None:
        df_bt["weekly_supertrend_bullish"] = weekly_supertrend_bullish.reindex(close.index)
    else:
        df_bt["weekly_supertrend_bullish"] = False

    # 4. Run Backtest
    bt = Backtest(
        df_bt, 
        TradeSentinelStrategy, 
        cash=initial_capital, 
        commission=0.0012, 
        exclusive_orders=True,
        trade_on_close=True
    )
    
    stats = bt.run(entry_strategy=entry_strategy, exit_strategy=exit_strategy)
    trades = stats["_trades"]
    
    years = (df.index[-1] - df.index[0]).days / 365.25
    strategy_return = stats.get("Return [%]", 0)
    bnh_return = stats.get("Buy & Hold Return [%]", 0)
    
    strat_cagr = ((1 + strategy_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
    bnh_cagr = ((1 + bnh_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
    exposure = stats.get("Exposure Time [%]", 0)
    
    total_profit_earned = 0.0
    total_loss_incurred = 0.0
    
    if not trades.empty:
        total_profit_earned = trades[trades['PnL'] > 0]['PnL'].sum()
        total_loss_incurred = trades[trades['PnL'] < 0]['PnL'].sum()

    # Add open trades PnL
    strategy_instance = stats.get("_strategy")
    if strategy_instance and hasattr(strategy_instance, "trades"):
        for t in strategy_instance.trades:
            if t.pl > 0:
                total_profit_earned += t.pl
            elif t.pl < 0:
                total_loss_incurred += t.pl
    
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
        "total_profit_earned": round(float(total_profit_earned), 2),
        "total_loss_incurred": round(float(total_loss_incurred), 2),
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

class TradeSentinelIntradayStrategy(Strategy):
    direction = "long"
    entry_strategy = 1
    exit_strategy = 1

    def init(self):
        self.entry_price = 0.0

    def next(self):
        # Calculate time in IST assuming data timestamp is UTC (if it is, add 5:30. But yfinance usually returns local time if timezone is set, or UTC. fetch_ohlcv ensures IST). 
        # Actually, df.index is tz-aware in pandas from yfinance. We can use .hour and .minute if it's in IST, or we convert.
        # Let's assume the timestamp is correct, or just use hour and minute directly if tz-aware.
        idx = self.data.df.index[-1]
        if idx.tz is None:
            # Assume UTC, add 5h30m
            current_time_ist = idx + pd.Timedelta(hours=5, minutes=30)
        else:
            # Convert to Asia/Kolkata
            current_time_ist = idx.tz_convert('Asia/Kolkata')
            
        current_hour = current_time_ist.hour
        current_minute = current_time_ist.minute
        current_time_hm = current_hour * 100 + current_minute

        close = self.data.Close[-1]
        high = self.data.High[-1]
        low = self.data.Low[-1]
        vwap = self.data.vwap[-1] if 'vwap' in self.data.df.columns else np.nan
        ema_9 = self.data.ema_9[-1] if 'ema_9' in self.data.df.columns else np.nan
        ema_21 = self.data.ema_21[-1] if 'ema_21' in self.data.df.columns else np.nan
        ema_9_prev = self.data.ema_9[-2] if 'ema_9' in self.data.df.columns and len(self.data.ema_9) > 1 else np.nan
        ema_21_prev = self.data.ema_21[-2] if 'ema_21' in self.data.df.columns and len(self.data.ema_21) > 1 else np.nan
        st = self.data.supertrend_direction[-1] if 'supertrend_direction' in self.data.df.columns else 0
        st_prev = self.data.supertrend_direction[-2] if 'supertrend_direction' in self.data.df.columns and len(self.data.supertrend_direction) > 1 else 0
        rsi = self.data.rsi[-1] if 'rsi' in self.data.df.columns else np.nan
        macd_line = self.data.macd_line[-1] if 'macd_line' in self.data.df.columns else np.nan
        macd_signal = self.data.macd_signal[-1] if 'macd_signal' in self.data.df.columns else np.nan
        
        # 15:15 Auto Square Off
        if current_time_hm >= 1515 and self.position:
            self.position.close()
            self.entry_price = 0.0
            return
            
        if not self.position:
            # Only allow new entries between 09:15 and 15:00
            if current_time_hm >= 915 and current_time_hm <= 1500:
                enter_trade = False
                
                if self.entry_strategy == 1:
                    if self.direction == "long":
                        if close > vwap and st == 1 and rsi > 60 and macd_line > macd_signal:
                            enter_trade = True
                    else:
                        if close < vwap and st == -1 and rsi < 40 and macd_line < macd_signal:
                            enter_trade = True
                
                elif self.entry_strategy == 2:
                    vwap_prev = self.data.vwap[-2] if len(self.data.vwap) > 1 else np.nan
                    close_prev = self.data.Close[-2] if len(self.data.Close) > 1 else np.nan
                    if self.direction == "long":
                        if close_prev < vwap_prev and close > vwap and rsi > 50:
                            enter_trade = True
                    else:
                        if close_prev > vwap_prev and close < vwap and rsi < 50:
                            enter_trade = True
                            
                elif self.entry_strategy == 3:
                    if self.direction == "long":
                        if ema_9_prev <= ema_21_prev and ema_9 > ema_21:
                            enter_trade = True
                    else:
                        if ema_9_prev >= ema_21_prev and ema_9 < ema_21:
                            enter_trade = True
                            
                elif self.entry_strategy == 4:
                    if self.direction == "long":
                        if st_prev == -1 and st == 1:
                            enter_trade = True
                    else:
                        if st_prev == 1 and st == -1:
                            enter_trade = True

                if enter_trade:
                    if self.direction == "long":
                        self.buy()
                    else:
                        self.sell()
                    self.entry_price = close
        else:
            exit_triggered = False
            
            if self.exit_strategy == 1:
                if self.direction == "long":
                    if st == -1 or close < vwap:
                        exit_triggered = True
                else:
                    if st == 1 or close > vwap:
                        exit_triggered = True
                        
            elif self.exit_strategy == 2:
                if self.entry_price > 0:
                    if self.direction == "long":
                        sl = self.entry_price * 0.995
                        tp = self.entry_price * 1.01
                        if low <= sl or high >= tp:
                            exit_triggered = True
                    else:
                        sl = self.entry_price * 1.005
                        tp = self.entry_price * 0.99
                        if high >= sl or low <= tp:
                            exit_triggered = True
                            
            elif self.exit_strategy == 3:
                if self.direction == "long":
                    if st == -1:
                        exit_triggered = True
                else:
                    if st == 1:
                        exit_triggered = True
                        
            elif self.exit_strategy == 4:
                if self.direction == "long":
                    if close < vwap:
                        exit_triggered = True
                else:
                    if close > vwap:
                        exit_triggered = True
                        
            elif self.exit_strategy == 5:
                pass
                
            if exit_triggered:
                self.position.close()
                self.entry_price = 0.0

def run_intraday_backtest(
    ticker: str, 
    direction: str = "long",
    initial_capital: float = 100000.0,
    entry_strategy: int = 1,
    exit_strategy: int = 1
) -> Dict[str, Any]:
    df = fetch_ohlcv(ticker, interval="5m", period="60d", use_cache=False)
    if df.empty:
        raise ValueError(f"No data available for {ticker}")

    ind = calculate_indicators(df, mode="intraday", include_series=True)
    if ind is None or not ind.series:
        raise ValueError(f"Insufficient data to calculate indicators for {ticker}")

    series = ind.series
    close_col = "adj close" if "adj close" in df.columns else "close"
    df_bt = df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        close_col: "Close",
        "volume": "Volume"
    }).copy()
    
    close = df_bt["Close"]
    
    for key in ["vwap", "ema_9", "ema_21", "supertrend_direction", "rsi", "macd_line", "macd_signal"]:
        val = series.get(key)
        if val is not None:
            df_bt[key] = val.reindex(close.index)
        else:
            df_bt[key] = np.nan

    bt = Backtest(
        df_bt, 
        TradeSentinelIntradayStrategy, 
        cash=initial_capital, 
        commission=0.0003,
        exclusive_orders=True,
        trade_on_close=True
    )
    
    stats = bt.run(
        direction=direction, 
        entry_strategy=entry_strategy, 
        exit_strategy=exit_strategy
    )
    
    trades = stats["_trades"]
    
    days = (df.index[-1] - df.index[0]).days
    years = days / 365.25 if days > 0 else 0
    strategy_return = stats.get("Return [%]", 0)
    bnh_return = stats.get("Buy & Hold Return [%]", 0)
    
    strat_cagr = ((1 + strategy_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
    bnh_cagr = ((1 + bnh_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
    exposure = stats.get("Exposure Time [%]", 0)
    
    total_profit_earned = 0.0
    total_loss_incurred = 0.0
    
    if not trades.empty:
        total_profit_earned = trades[trades['PnL'] > 0]['PnL'].sum()
        total_loss_incurred = trades[trades['PnL'] < 0]['PnL'].sum()

    strategy_instance = stats.get("_strategy")
    if strategy_instance and hasattr(strategy_instance, "trades"):
        for t in strategy_instance.trades:
            if t.pl > 0:
                total_profit_earned += t.pl
            elif t.pl < 0:
                total_loss_incurred += t.pl
    
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
        "total_profit_earned": round(float(total_profit_earned), 2),
        "total_loss_incurred": round(float(total_loss_incurred), 2),
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

