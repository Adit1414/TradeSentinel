from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

from app.services.backtest_engine import run_backtest, run_intraday_backtest

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])

class BacktestRequest(BaseModel):
    ticker: str
    period: str = "5y"
    initial_capital: float = 100000.0
    entry_strategy: int = 1
    sell_threshold: int = 3
    exit_strategy: int = 2

@router.post("/run")
def execute_backtest(request: BacktestRequest) -> Dict[str, Any]:
    """Run a backtest for a specific ticker and return the performance stats and trades."""
    try:
        results = run_backtest(
            ticker=request.ticker,
            period=request.period,
            initial_capital=request.initial_capital,
            entry_strategy=request.entry_strategy,
            sell_threshold=request.sell_threshold,
            exit_strategy=request.exit_strategy
        )
        return results
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest error: {str(e)}")

class BatchBacktestRequest(BaseModel):
    tickers: List[str]
    period: str = "5y"
    initial_capital: float = 100000.0
    entry_strategy: int = 1
    sell_threshold: int = 3
    exit_strategy: int = 2

@router.post("/batch")
def execute_batch_backtest(request: BatchBacktestRequest) -> List[Dict[str, Any]]:
    """Run backtests for multiple tickers and return summary stats for each."""
    results = []
    for ticker in request.tickers:
        try:
            res = run_backtest(
                ticker=ticker,
                period=request.period,
                initial_capital=request.initial_capital,
                entry_strategy=request.entry_strategy,
                sell_threshold=request.sell_threshold,
                exit_strategy=request.exit_strategy
            )
            stats = res["stats"]
            stats["ticker"] = ticker
            results.append(stats)
        except Exception as e:
            # Note the error but continue with other tickers
            results.append({
                "ticker": ticker,
                "error": str(e)
            })
    return results

class IntradayBacktestRequest(BaseModel):
    ticker: str
    direction: str = "long"
    initial_capital: float = 100000.0
    entry_strategy: int = 1
    exit_strategy: int = 1

@router.post("/intraday")
def execute_intraday_backtest(request: IntradayBacktestRequest) -> Dict[str, Any]:
    """Run an intraday backtest (5m candles, 60 days)."""
    try:
        results = run_intraday_backtest(
            ticker=request.ticker,
            direction=request.direction,
            initial_capital=request.initial_capital,
            entry_strategy=request.entry_strategy,
            exit_strategy=request.exit_strategy
        )
        return results
    except ValueError as e:
        # Check if rate limited
        if "HTTP 429" in str(e) or "Crumb fetch" in str(e) or "No data available" in str(e):
            raise HTTPException(status_code=429, detail=f"No Data / Rate Limited: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if "HTTP 429" in str(e) or "Crumb fetch" in str(e):
            raise HTTPException(status_code=429, detail=f"Rate Limited: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Backtest error: {str(e)}")
