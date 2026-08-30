import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.backtest_engine import run_backtest

try:
    results = run_backtest("RELIANCE.NS", "5y", 100000.0, 3, 3)
    print("Stats:")
    for k, v in results["stats"].items():
        print(f"  {k}: {v}")
    
    print("\nTrades:")
    for t in results["trades"][:3]: # print first 3 trades
        print(t)
        
    print(f"\nTotal trades executed: {len(results['trades'])}")
except Exception as e:
    print(f"Error: {e}")
