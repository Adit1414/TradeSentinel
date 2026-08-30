from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

from app.services.backtest_engine import run_backtest

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
