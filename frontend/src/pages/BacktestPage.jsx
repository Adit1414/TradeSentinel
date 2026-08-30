import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Play, TrendingUp, AlertCircle, Percent, DollarSign, Activity } from 'lucide-react';
import { backtestApi, watchlistApi } from '../api/client';
import './Pages.css';

export default function BacktestPage() {
  const [ticker, setTicker] = useState('RELIANCE.NS');
  const [period, setPeriod] = useState('10y');
  const [capital, setCapital] = useState(100000);
  const [entryStrategy, setEntryStrategy] = useState(1);
  const [exitStrategy, setExitStrategy] = useState(2);

  const mutation = useMutation({
    mutationFn: (data) => backtestApi.run(data).then((r) => r.data),
  });

  const batchMutation = useMutation({
    mutationFn: async (data) => {
      const { data: watchlist } = await watchlistApi.listAll();
      const allTickers = watchlist.map((item) => item.ticker);
      const tickers = [...new Set(allTickers)];
      if (tickers.length === 0) throw new Error('No tickers in watchlist');
      return backtestApi.batchRun({ ...data, tickers }).then((r) => r.data);
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!ticker) return;
    
    // Ensure ticker has .NS suffix
    let cleanTicker = ticker.trim().toUpperCase();
    if (!cleanTicker.endsWith('.NS')) {
      cleanTicker += '.NS';
    }

    mutation.mutate({
      ticker: cleanTicker,
      period,
      initial_capital: parseFloat(capital),
      entry_strategy: parseInt(entryStrategy),
      exit_strategy: parseInt(exitStrategy),
    });
  };

  const handleBatchSubmit = (e) => {
    e.preventDefault();
    batchMutation.mutate({
      period,
      initial_capital: parseFloat(capital),
      entry_strategy: parseInt(entryStrategy),
      exit_strategy: parseInt(exitStrategy),
    });
  };

  const stats = mutation.data?.stats;
  const trades = mutation.data?.trades;
  const batchData = batchMutation.data;

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h1 className="page-title">Long-Term Backtester</h1>
          <p className="page-subtitle">Test the 4-indicator confluence strategy against historical data.</p>
        </div>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 'var(--space-xl)', alignItems: 'start' }}>
        
        {/* Configuration Panel */}
        <div className="glass-card" style={{ padding: 'var(--space-lg)' }}>
          <h3 style={{ marginBottom: 'var(--space-md)', fontSize: '1rem' }}>Configuration</h3>
          
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            <div className="form-group">
              <label className="form-label">Ticker Symbol</label>
              <input
                type="text"
                className="input"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                placeholder="e.g. RELIANCE.NS"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Duration</label>
              <select className="input" value={period} onChange={(e) => setPeriod(e.target.value)}>
                <option value="1y">1 Year</option>
                <option value="2y">2 Years</option>
                <option value="5y">5 Years</option>
                <option value="10y">10 Years</option>
                <option value="max">Max Available</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Initial Capital (₹)</label>
              <input
                type="number"
                className="input"
                value={capital}
                onChange={(e) => setCapital(e.target.value)}
                min="1000"
                step="1000"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Entry Strategy</label>
              <select className="input" value={entryStrategy} onChange={(e) => setEntryStrategy(e.target.value)}>
                <option value="1">1. Deep Value (3-of-4 Indicators)</option>
                <option value="2">2. Macro Trend Follower (10W/40W EMA Cross)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Exit Strategy</label>
              <select className="input" value={exitStrategy} onChange={(e) => setExitStrategy(e.target.value)}>
                <option value="1">1. Pure Oscillators (RSI &gt; 70 or BB Upper)</option>
                <option value="2">2. Structural Breakdown (Trailing Stop or 200 SMA Loss)</option>
                <option value="3">3. Macro Momentum Shift (RSI &gt; 70 + MACD Bearish)</option>
                <option value="4">4. Macro Trend Breakdown (10W &lt; 40W EMA)</option>
              </select>
            </div>

            <div style={{ display: 'flex', gap: '8px', marginTop: 'var(--space-md)' }}>
              <button 
                type="submit" 
                className="btn btn-primary" 
                style={{ flex: 1, padding: '0.5rem' }}
                disabled={mutation.isPending || batchMutation.isPending}
              >
                {mutation.isPending ? (
                  <span className="animate-pulse">Running...</span>
                ) : (
                  <>
                    <Play size={16} />
                    Run
                  </>
                )}
              </button>
              
              <button 
                type="button" 
                onClick={handleBatchSubmit}
                className="btn" 
                style={{ flex: 1, backgroundColor: 'var(--bg-lighter)', color: 'var(--text-color)', border: '1px solid var(--border-color)', padding: '0.5rem' }}
                disabled={mutation.isPending || batchMutation.isPending}
                title="Run backtest on all unique tickers in your watchlists"
              >
                {batchMutation.isPending ? (
                  <span className="animate-pulse">Batching...</span>
                ) : (
                  <>
                    <Activity size={16} />
                    Batch
                  </>
                )}
              </button>
            </div>
          </form>

          {mutation.isError && (
            <div className="alert alert-error" style={{ marginTop: 'var(--space-lg)' }}>
              <AlertCircle size={16} />
              <div className="alert-content">
                <span className="alert-title">Backtest Failed</span>
                <span className="alert-desc">{mutation.error.response?.data?.detail || mutation.error.message}</span>
              </div>
            </div>
          )}

          {batchMutation.isError && (
            <div className="alert alert-error" style={{ marginTop: 'var(--space-lg)' }}>
              <AlertCircle size={16} />
              <div className="alert-content">
                <span className="alert-title">Batch Backtest Failed</span>
                <span className="alert-desc">{batchMutation.error.response?.data?.detail || batchMutation.error.message}</span>
              </div>
            </div>
          )}
        </div>

        {/* Results View */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xl)' }}>
          
          {!stats && !batchData && !mutation.isPending && !batchMutation.isPending && (
            <div className="empty-state glass-card" style={{ padding: '64px 32px' }}>
              <Activity size={48} strokeWidth={1} style={{ marginBottom: 16, opacity: 0.5 }} />
              <h3>Ready to backtest</h3>
              <p>Configure your strategy rules on the left and run the simulation.</p>
              <p style={{ fontSize: '12px', marginTop: 12 }}>Note: Commission is set to exactly 0.12% per trade to simulate NSE delivery statutory charges.</p>
            </div>
          )}

          )}

          {/* Aggregate Calculation */}
          {(() => {
            if (!batchData || batchData.length === 0) return null;
            const validData = batchData.filter(d => !d.error);
            const n = validData.length;
            if (n === 0) return null;
            
            const agg = {
              return_pct: (validData.reduce((acc, curr) => acc + curr.return_pct, 0) / n).toFixed(2),
              buy_hold_return_pct: (validData.reduce((acc, curr) => acc + curr.buy_hold_return_pct, 0) / n).toFixed(2),
              strategy_cagr_pct: (validData.reduce((acc, curr) => acc + curr.strategy_cagr_pct, 0) / n).toFixed(2),
              buy_hold_cagr_pct: (validData.reduce((acc, curr) => acc + curr.buy_hold_cagr_pct, 0) / n).toFixed(2),
              win_rate_pct: (validData.reduce((acc, curr) => acc + curr.win_rate_pct, 0) / n).toFixed(2),
              total_trades: validData.reduce((acc, curr) => acc + curr.total_trades, 0),
              cash_drag_pct: (validData.reduce((acc, curr) => acc + curr.cash_drag_pct, 0) / n).toFixed(2),
              max_drawdown_pct: (validData.reduce((acc, curr) => acc + curr.max_drawdown_pct, 0) / n).toFixed(2),
              total_profit_earned: validData.reduce((acc, curr) => acc + curr.total_profit_earned, 0).toFixed(2),
              total_loss_incurred: validData.reduce((acc, curr) => acc + curr.total_loss_incurred, 0).toFixed(2)
            };

            return (
              <div className="glass-card">
                <div style={{ padding: 'var(--space-lg)', borderBottom: '1px solid var(--border-color)' }}>
                  <h3 style={{ fontSize: '1rem' }}>Batch Watchlist Results</h3>
                </div>
                <div className="table-responsive">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Ticker</th>
                        <th style={{ textAlign: 'right' }}>Total Return %</th>
                        <th style={{ textAlign: 'right' }}>B&H Return %</th>
                        <th style={{ textAlign: 'right' }}>CAGR %</th>
                        <th style={{ textAlign: 'right' }}>B&H CAGR %</th>
                        <th style={{ textAlign: 'right' }}>Win Rate</th>
                        <th style={{ textAlign: 'right' }}>Trades</th>
                        <th style={{ textAlign: 'right' }}>Cash Drag</th>
                        <th style={{ textAlign: 'right' }}>Max DD</th>
                        <th style={{ textAlign: 'right' }}>Total Profit (₹)</th>
                        <th style={{ textAlign: 'right' }}>Total Loss (₹)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {batchData.map((res, idx) => (
                        <tr key={idx}>
                          <td className="mono" style={{ fontWeight: 600 }}>{res.ticker}</td>
                          {res.error ? (
                            <td colSpan="10" style={{ color: 'var(--red)', fontSize: '12px' }}>{res.error}</td>
                          ) : (
                            <>
                              <td style={{ textAlign: 'right', color: res.return_pct > 0 ? 'var(--green)' : 'var(--red)' }} className="mono">{res.return_pct > 0 ? '+' : ''}{res.return_pct}%</td>
                              <td style={{ textAlign: 'right' }} className="mono">{res.buy_hold_return_pct}%</td>
                              <td style={{ textAlign: 'right', color: res.strategy_cagr_pct > 0 ? 'var(--green)' : 'var(--red)' }} className="mono">{res.strategy_cagr_pct > 0 ? '+' : ''}{res.strategy_cagr_pct}%</td>
                              <td style={{ textAlign: 'right' }} className="mono">{res.buy_hold_cagr_pct}%</td>
                              <td style={{ textAlign: 'right' }} className="mono">{res.win_rate_pct}%</td>
                              <td style={{ textAlign: 'right' }} className="mono">{res.total_trades}</td>
                              <td style={{ textAlign: 'right' }} className="mono">{res.cash_drag_pct}%</td>
                              <td style={{ textAlign: 'right', color: 'var(--red)' }} className="mono">{res.max_drawdown_pct}%</td>
                              <td style={{ textAlign: 'right', color: 'var(--green)' }} className="mono">{res.total_profit_earned > 0 ? '+' : ''}{res.total_profit_earned}</td>
                              <td style={{ textAlign: 'right', color: 'var(--red)' }} className="mono">{res.total_loss_incurred}</td>
                            </>
                          )}
                        </tr>
                      ))}
                      {/* Aggregate Row */}
                      <tr style={{ backgroundColor: 'var(--bg-lighter)' }}>
                        <td className="mono" style={{ fontWeight: 700 }}>AGGREGATE ({n} valid)</td>
                        <td style={{ textAlign: 'right', fontWeight: 700, color: agg.return_pct > 0 ? 'var(--green)' : 'var(--red)' }} className="mono">{agg.return_pct > 0 ? '+' : ''}{agg.return_pct}%</td>
                        <td style={{ textAlign: 'right', fontWeight: 700 }} className="mono">{agg.buy_hold_return_pct}%</td>
                        <td style={{ textAlign: 'right', fontWeight: 700, color: agg.strategy_cagr_pct > 0 ? 'var(--green)' : 'var(--red)' }} className="mono">{agg.strategy_cagr_pct > 0 ? '+' : ''}{agg.strategy_cagr_pct}%</td>
                        <td style={{ textAlign: 'right', fontWeight: 700 }} className="mono">{agg.buy_hold_cagr_pct}%</td>
                        <td style={{ textAlign: 'right', fontWeight: 700 }} className="mono">{agg.win_rate_pct}%</td>
                        <td style={{ textAlign: 'right', fontWeight: 700 }} className="mono">{agg.total_trades}</td>
                        <td style={{ textAlign: 'right', fontWeight: 700 }} className="mono">{agg.cash_drag_pct}%</td>
                        <td style={{ textAlign: 'right', fontWeight: 700, color: 'var(--red)' }} className="mono">{agg.max_drawdown_pct}%</td>
                        <td style={{ textAlign: 'right', fontWeight: 700, color: 'var(--green)' }} className="mono">{agg.total_profit_earned > 0 ? '+' : ''}{agg.total_profit_earned}</td>
                        <td style={{ textAlign: 'right', fontWeight: 700, color: 'var(--red)' }} className="mono">{agg.total_loss_incurred}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })()}

          {/* Single Ticker Results */}
          {stats && (
            <>
              {/* Summary Stats Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-lg)' }}>
                
                <div className="glass-card" style={{ padding: 'var(--space-lg)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: 'var(--text-muted)' }}>
                    <Percent size={16} /> 
                    <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Total Return</span>
                  </div>
                  <div style={{ fontSize: '32px', fontWeight: 700, color: stats.return_pct > 0 ? 'var(--green)' : 'var(--red)' }}>
                    {stats.return_pct > 0 ? '+' : ''}{stats.return_pct}%
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: 4 }}>
                    vs {stats.buy_hold_return_pct}% Buy & Hold
                  </div>
                </div>

                <div className="glass-card" style={{ padding: 'var(--space-lg)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: 'var(--text-muted)' }}>
                    <Percent size={16} /> 
                    <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Strategy CAGR</span>
                  </div>
                  <div style={{ fontSize: '32px', fontWeight: 700, color: stats.strategy_cagr_pct > 0 ? 'var(--green)' : 'var(--red)' }}>
                    {stats.strategy_cagr_pct > 0 ? '+' : ''}{stats.strategy_cagr_pct}%
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: 4 }}>
                    vs {stats.buy_hold_cagr_pct}% Buy & Hold
                  </div>
                </div>

                <div className="glass-card" style={{ padding: 'var(--space-lg)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: 'var(--text-muted)' }}>
                    <TrendingUp size={16} /> 
                    <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Win Rate</span>
                  </div>
                  <div style={{ fontSize: '32px', fontWeight: 700 }}>
                    {stats.win_rate_pct}%
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: 4 }}>
                    {stats.total_trades} total trades
                  </div>
                </div>

                <div className="glass-card" style={{ padding: 'var(--space-lg)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: 'var(--text-muted)' }}>
                    <Activity size={16} /> 
                    <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Max Drawdown</span>
                  </div>
                  <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--red)' }}>
                    {stats.max_drawdown_pct}%
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: 4 }}>
                    Largest peak-to-trough drop
                  </div>
                </div>

                <div className="glass-card" style={{ padding: 'var(--space-lg)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: 'var(--text-muted)' }}>
                    <DollarSign size={16} /> 
                    <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Cash Drag</span>
                  </div>
                  <div style={{ fontSize: '32px', fontWeight: 700 }}>
                    {stats.cash_drag_pct}%
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: 4 }}>
                    Time spent out of market
                  </div>
                </div>

              </div>

              {/* Trades Table */}
              <div className="glass-card">
                <div style={{ padding: 'var(--space-lg)', borderBottom: '1px solid var(--border-color)' }}>
                  <h3 style={{ fontSize: '1rem' }}>Trade History ({stats.total_trades})</h3>
                </div>
                
                {trades && trades.length > 0 ? (
                  <div className="table-responsive">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Entry Date</th>
                          <th>Exit Date</th>
                          <th style={{ textAlign: 'right' }}>Entry Price</th>
                          <th style={{ textAlign: 'right' }}>Exit Price</th>
                          <th style={{ textAlign: 'right' }}>Shares</th>
                          <th style={{ textAlign: 'right' }}>PnL (₹)</th>
                          <th style={{ textAlign: 'right' }}>Return</th>
                        </tr>
                      </thead>
                      <tbody>
                        {trades.map((trade, idx) => (
                          <tr key={idx}>
                            <td className="mono">{trade.entry_time.split(' ')[0]}</td>
                            <td className="mono">{trade.exit_time ? trade.exit_time.split(' ')[0] : 'Open'}</td>
                            <td style={{ textAlign: 'right' }} className="mono">{trade.entry_price.toFixed(2)}</td>
                            <td style={{ textAlign: 'right' }} className="mono">{trade.exit_price ? trade.exit_price.toFixed(2) : '-'}</td>
                            <td style={{ textAlign: 'right' }} className="mono">{trade.size}</td>
                            <td style={{ textAlign: 'right', color: trade.pnl > 0 ? 'var(--green)' : 'var(--red)' }} className="mono">
                              {trade.pnl > 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                            </td>
                            <td style={{ textAlign: 'right', color: trade.return_pct > 0 ? 'var(--green)' : 'var(--red)' }} className="mono">
                              {trade.return_pct > 0 ? '+' : ''}{trade.return_pct.toFixed(2)}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div style={{ padding: 'var(--space-xl)', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No trades were executed with these parameters.
                  </div>
                )}
              </div>
            </>
          )}

        </div>
      </div>
    </div>
  );
}
