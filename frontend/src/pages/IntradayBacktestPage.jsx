import { useState, useRef } from 'react';
import { Play, TrendingUp, AlertCircle, Percent, DollarSign, Activity, XCircle } from 'lucide-react';
import { backtestApi, watchlistApi } from '../api/client';
import './Pages.css';

export default function IntradayBacktestPage() {
  const [ticker, setTicker] = useState('RELIANCE.NS');
  const [direction, setDirection] = useState('long');
  const [capital, setCapital] = useState(100000);
  const [entryStrategy, setEntryStrategy] = useState(1);
  const [exitStrategy, setExitStrategy] = useState(1);

  // Single Run State
  const [singleResult, setSingleResult] = useState(null);
  const [isSingleRunning, setIsSingleRunning] = useState(false);
  const [singleError, setSingleError] = useState(null);

  // Batch Run State
  const [isBatchRunning, setIsBatchRunning] = useState(false);
  const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0, currentTicker: '' });
  const [batchResults, setBatchResults] = useState([]);
  const [estimatedTimeLeft, setEstimatedTimeLeft] = useState(0);
  
  const abortControllerRef = useRef(null);

  const handleSingleSubmit = async (e) => {
    e.preventDefault();
    if (!ticker) return;

    let cleanTicker = ticker.trim().toUpperCase();
    if (!cleanTicker.endsWith('.NS')) {
      cleanTicker += '.NS';
    }

    setIsSingleRunning(true);
    setSingleError(null);
    setSingleResult(null);

    try {
      const response = await backtestApi.intradayRun({
        ticker: cleanTicker,
        direction,
        initial_capital: parseFloat(capital),
        entry_strategy: parseInt(entryStrategy),
        exit_strategy: parseInt(exitStrategy),
      });
      setSingleResult(response.data);
    } catch (err) {
      setSingleError(err.response?.data?.detail || err.message);
    } finally {
      setIsSingleRunning(false);
    }
  };

  const runBatchBacktest = async () => {
    try {
      const { data: watchlist } = await watchlistApi.listAll();
      const allTickers = watchlist.map((item) => item.ticker);
      const tickers = [...new Set(allTickers)];
      
      if (tickers.length === 0) {
        alert("No tickers in watchlist");
        return;
      }

      setIsBatchRunning(true);
      setBatchResults([]);
      setBatchProgress({ current: 0, total: tickers.length, currentTicker: tickers[0] });
      setEstimatedTimeLeft(tickers.length * 1.5);
      
      abortControllerRef.current = new AbortController();
      const newResults = [];

      for (let i = 0; i < tickers.length; i++) {
        if (abortControllerRef.current?.signal.aborted) {
          break;
        }

        const currentTicker = tickers[i];
        setBatchProgress({ current: i, total: tickers.length, currentTicker });
        setEstimatedTimeLeft(Math.max(0, (tickers.length - i) * 1.5));

        try {
          const response = await backtestApi.intradayRun({
            ticker: currentTicker,
            direction,
            initial_capital: parseFloat(capital),
            entry_strategy: parseInt(entryStrategy),
            exit_strategy: parseInt(exitStrategy),
          });
          
          const stats = response.data.stats;
          stats.ticker = currentTicker;
          newResults.push(stats);
          setBatchResults([...newResults]);
          
          // Smart Throttling: Success delay
          await new Promise(r => setTimeout(r, 400));
        } catch (err) {
          const errMsg = err.response?.data?.detail || err.message;
          console.warn(`Error backtesting ${currentTicker}:`, errMsg);
          
          newResults.push({
            ticker: currentTicker,
            error: errMsg
          });
          setBatchResults([...newResults]);

          // Penalty Delay on Rate Limit or Error
          await new Promise(r => setTimeout(r, 3000));
        }
      }
    } catch (err) {
      console.error(err);
      alert("Failed to start batch process: " + err.message);
    } finally {
      setIsBatchRunning(false);
      abortControllerRef.current = null;
    }
  };

  const handleCancelBatch = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const stats = singleResult?.stats;
  const trades = singleResult?.trades;
  
  // Batch aggregate stats
  const successfulBatch = batchResults.filter(r => !r.error);
  const batchAgg = successfulBatch.length > 0 ? {
    avgReturn: successfulBatch.reduce((acc, curr) => acc + curr.return_pct, 0) / successfulBatch.length,
    avgWinRate: successfulBatch.reduce((acc, curr) => acc + curr.win_rate_pct, 0) / successfulBatch.length,
    totalProfit: successfulBatch.reduce((acc, curr) => acc + curr.total_profit_earned, 0),
    totalLoss: successfulBatch.reduce((acc, curr) => acc + curr.total_loss_incurred, 0),
    avgTrades: successfulBatch.reduce((acc, curr) => acc + curr.total_trades, 0) / successfulBatch.length,
  } : null;

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h1 className="page-title">Intraday Backtester</h1>
          <p className="page-subtitle">Test fast 5-minute modular strategies (09:15-15:15 IST).</p>
        </div>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 'var(--space-xl)', alignItems: 'start' }}>
        
        {/* Configuration Panel */}
        <div className="glass-card" style={{ padding: 'var(--space-lg)' }}>
          <h3 style={{ marginBottom: 'var(--space-md)', fontSize: '1rem' }}>Configuration</h3>
          
          <form onSubmit={handleSingleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            <div className="form-group">
              <label className="form-label">Ticker Symbol</label>
              <input
                type="text"
                className="input"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                placeholder="e.g. RELIANCE.NS"
                required
                disabled={isBatchRunning || isSingleRunning}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Direction</label>
              <select 
                className="input" 
                value={direction} 
                onChange={(e) => setDirection(e.target.value)}
                disabled={isBatchRunning || isSingleRunning}
              >
                <option value="long">1. Long</option>
                <option value="short">2. Short</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Entry Strategy</label>
              <select 
                className="input" 
                value={entryStrategy} 
                onChange={(e) => setEntryStrategy(e.target.value)}
                disabled={isBatchRunning || isSingleRunning}
              >
                <option value="1">1. Original 4-Indicator Confluence</option>
                <option value="2">2. VWAP Reversion</option>
                <option value="3">3. 9/21 EMA Momentum Cross</option>
                <option value="4">4. Supertrend Breakout</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Exit Strategy</label>
              <select 
                className="input" 
                value={exitStrategy} 
                onChange={(e) => setExitStrategy(e.target.value)}
                disabled={isBatchRunning || isSingleRunning}
              >
                <option value="1">1. Original Confluence Break (Loss of Momentum)</option>
                <option value="2">2. Fixed Risk:Reward (1:2)</option>
                <option value="3">3. Supertrend Trailing Stop</option>
                <option value="4">4. VWAP Loss</option>
                <option value="5">5. End of Day Only (Run the Clock)</option>
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
                disabled={isBatchRunning || isSingleRunning}
              />
            </div>
            
            {isBatchRunning ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: 'var(--space-md)' }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  Testing {batchProgress.currentTicker}... ({batchProgress.current + 1} of {batchProgress.total})
                </div>
                <div style={{ 
                  width: '100%', 
                  height: '6px', 
                  backgroundColor: 'rgba(255,255,255,0.1)', 
                  borderRadius: '3px',
                  overflow: 'hidden'
                }}>
                  <div style={{ 
                    height: '100%', 
                    width: `${batchProgress.total > 0 ? ((batchProgress.current + 1) / batchProgress.total) * 100 : 0}%`, 
                    backgroundColor: 'var(--accent)',
                    transition: 'width 0.3s ease'
                  }}></div>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  Estimated time remaining: ~{Math.ceil(estimatedTimeLeft)}s
                </div>
                <button 
                  type="button"
                  className="btn btn-outline" 
                  onClick={handleCancelBatch}
                  style={{ width: '100%', marginTop: '4px', borderColor: 'var(--danger)', color: 'var(--danger)' }}
                >
                  <XCircle size={16} /> Cancel Batch
                </button>
              </div>
            ) : (
              <>
                <button 
                  type="submit" 
                  className="btn btn-primary" 
                  style={{ width: '100%', marginTop: 'var(--space-md)' }}
                  disabled={isSingleRunning}
                >
                  {isSingleRunning ? (
                    'Running...'
                  ) : (
                    <><Play size={16} /> Run Backtest</>
                  )}
                </button>

                <button 
                  type="button"
                  className="btn btn-outline" 
                  style={{ width: '100%' }}
                  onClick={runBatchBacktest}
                  disabled={isSingleRunning}
                >
                  <Activity size={16} /> Batch Test Watchlist
                </button>
              </>
            )}
            
            {singleError && (
              <div style={{ marginTop: '1rem', color: 'var(--danger)', fontSize: '0.85rem' }}>
                <AlertCircle size={14} style={{ display: 'inline', marginRight: '4px' }}/>
                {singleError}
              </div>
            )}
          </form>
        </div>

        {/* Results Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
          
          {batchResults.length > 0 ? (
            <>
              {/* BATCH RESULTS */}
              <div className="glass-card" style={{ padding: 'var(--space-lg)' }}>
                <h2 style={{ fontSize: '1.2rem', marginBottom: 'var(--space-md)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Activity size={20} className="text-accent" /> Batch Results ({batchResults.length} / {batchProgress.total})
                </h2>
                
                {batchAgg && (
                  <div className="metrics-grid" style={{ marginBottom: 'var(--space-xl)' }}>
                    <div className="metric-card">
                      <div className="metric-label">Avg Total Return</div>
                      <div className={`metric-value ${batchAgg.avgReturn >= 0 ? 'text-success' : 'text-danger'}`}>
                        {batchAgg.avgReturn.toFixed(2)}%
                      </div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">Avg Win Rate</div>
                      <div className="metric-value">{batchAgg.avgWinRate.toFixed(2)}%</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">Total Profit (Positives)</div>
                      <div className="metric-value text-success">₹{batchAgg.totalProfit.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">Total Loss (Negatives)</div>
                      <div className="metric-value text-danger">₹{batchAgg.totalLoss.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
                    </div>
                  </div>
                )}

                <div className="table-container" style={{ maxHeight: '600px', overflowY: 'auto' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Ticker</th>
                        <th>Status</th>
                        <th>Return %</th>
                        <th>Win Rate</th>
                        <th>Trades</th>
                        <th>Profit Earned</th>
                        <th>Loss Incurred</th>
                        <th>Max DD</th>
                      </tr>
                    </thead>
                    <tbody>
                      {batchResults.map((r, i) => (
                        <tr key={i}>
                          <td style={{ fontWeight: 500 }}>{r.ticker}</td>
                          {r.error ? (
                            <td colSpan="7" style={{ color: 'var(--danger)' }}>{r.error}</td>
                          ) : (
                            <>
                              <td className="text-success">Success</td>
                              <td className={r.return_pct >= 0 ? 'text-success' : 'text-danger'}>
                                {r.return_pct}%
                              </td>
                              <td>{r.win_rate_pct}%</td>
                              <td>{r.total_trades}</td>
                              <td className="text-success">₹{r.total_profit_earned?.toLocaleString()}</td>
                              <td className="text-danger">₹{r.total_loss_incurred?.toLocaleString()}</td>
                              <td className="text-danger">{r.max_drawdown_pct}%</td>
                            </>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : stats ? (
            <>
              {/* SINGLE RESULTS */}
              <div className="glass-card" style={{ padding: 'var(--space-lg)' }}>
                <h2 style={{ fontSize: '1.2rem', marginBottom: 'var(--space-md)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <TrendingUp size={20} className="text-accent" /> Performance Summary
                </h2>
                <div className="metrics-grid">
                  <div className="metric-card">
                    <div className="metric-icon"><Percent size={20} /></div>
                    <div className="metric-label">Total Return</div>
                    <div className={`metric-value ${stats.return_pct >= 0 ? 'text-success' : 'text-danger'}`}>
                      {stats.return_pct}%
                    </div>
                  </div>
                  
                  <div className="metric-card">
                    <div className="metric-icon"><Activity size={20} /></div>
                    <div className="metric-label">Win Rate</div>
                    <div className="metric-value text-accent">{stats.win_rate_pct}%</div>
                  </div>

                  <div className="metric-card">
                    <div className="metric-icon"><TrendingUp size={20} /></div>
                    <div className="metric-label">Total Trades</div>
                    <div className="metric-value">{stats.total_trades}</div>
                  </div>

                  <div className="metric-card">
                    <div className="metric-icon"><AlertCircle size={20} /></div>
                    <div className="metric-label">Max Drawdown</div>
                    <div className="metric-value text-danger">{stats.max_drawdown_pct}%</div>
                  </div>
                  
                  <div className="metric-card">
                    <div className="metric-icon"><DollarSign size={20} /></div>
                    <div className="metric-label">Total Profit Earned</div>
                    <div className="metric-value text-success">₹{stats.total_profit_earned.toLocaleString('en-IN')}</div>
                  </div>
                  
                  <div className="metric-card">
                    <div className="metric-icon"><DollarSign size={20} /></div>
                    <div className="metric-label">Total Loss Incurred</div>
                    <div className="metric-value text-danger">₹{stats.total_loss_incurred.toLocaleString('en-IN')}</div>
                  </div>
                </div>
              </div>

              {trades && trades.length > 0 && (
                <div className="glass-card" style={{ padding: 'var(--space-lg)' }}>
                  <h3 style={{ marginBottom: 'var(--space-md)' }}>Trade Log</h3>
                  <div className="table-container" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Entry Time</th>
                          <th>Exit Time</th>
                          <th>Entry Price</th>
                          <th>Exit Price</th>
                          <th>PnL</th>
                          <th>Return %</th>
                          <th>Duration</th>
                        </tr>
                      </thead>
                      <tbody>
                        {trades.map((trade, idx) => (
                          <tr key={idx}>
                            <td>{new Date(trade.entry_time).toLocaleString()}</td>
                            <td>{trade.exit_time !== "Open" ? new Date(trade.exit_time).toLocaleString() : "Open"}</td>
                            <td>₹{trade.entry_price.toFixed(2)}</td>
                            <td>{trade.exit_time !== "Open" ? `₹${trade.exit_price.toFixed(2)}` : "-"}</td>
                            <td className={trade.pnl >= 0 ? 'text-success' : 'text-danger'}>
                              {trade.pnl >= 0 ? '+' : ''}₹{trade.pnl.toFixed(2)}
                            </td>
                            <td className={trade.return_pct >= 0 ? 'text-success' : 'text-danger'}>
                              {trade.return_pct >= 0 ? '+' : ''}{trade.return_pct.toFixed(2)}%
                            </td>
                            <td>{trade.duration}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="glass-card" style={{ padding: 'var(--space-xl)', textAlign: 'center', color: 'var(--text-secondary)' }}>
              <Activity size={48} style={{ margin: '0 auto var(--space-md)', opacity: 0.5 }} />
              <p>Configure and run a test to see intraday performance.</p>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
