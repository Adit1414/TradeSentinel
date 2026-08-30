from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

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
