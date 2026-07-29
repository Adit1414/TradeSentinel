import PriceChart from './PriceChart';
import RSIPanel from './RSIPanel';
import MACDPanel from './MACDPanel';
import './Chart.css';

/**
 * Orchestrator that stacks the main chart + sub-panels.
 */
export default function ChartContainer({ chartData, mode }) {
  if (!chartData) {
    return (
      <div className="chart-wrapper">
        <div className="chart-pane chart-pane-main flex-center" style={{ minHeight: 400 }}>
          <p style={{ color: 'var(--text-muted)' }}>Loading chart data...</p>
        </div>
      </div>
    );
  }

  const { candles, indicators, latest } = chartData;

  if (!candles?.length) {
    return (
      <div className="chart-wrapper">
        <div className="chart-pane chart-pane-main flex-center" style={{ minHeight: 400 }}>
          <p style={{ color: 'var(--text-muted)' }}>No chart data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chart-wrapper">
      {/* Indicator Status Bar */}
      {latest && Object.keys(latest).length > 0 && (
        <div className="indicator-bar">
          <div className="indicator-pill">
            <span className="indicator-label">Price</span>
            <span className="indicator-value mono">₹{latest.price?.toFixed(2)}</span>
          </div>

          {latest.vwap && (
            <div className="indicator-pill">
              <span className="indicator-label">VWAP</span>
              <span className={`indicator-value mono ${latest.price > latest.vwap ? 'price-up' : 'price-down'}`}>
                ₹{latest.vwap?.toFixed(2)}
              </span>
            </div>
          )}

          {latest.ema_200 && (
            <div className="indicator-pill">
              <span className="indicator-label">200 EMA</span>
              <span className={`indicator-value mono ${latest.price > latest.ema_200 ? 'price-up' : 'price-down'}`}>
                ₹{latest.ema_200?.toFixed(2)}
              </span>
            </div>
          )}

          <div className="indicator-pill">
            <span className="indicator-label">Supertrend</span>
            <span className={`indicator-value ${latest.supertrend_direction === 1 ? 'price-up' : 'price-down'}`}>
              {latest.supertrend_direction === 1 ? '▲ Bullish' : '▼ Bearish'}
            </span>
          </div>

          <div className="indicator-pill">
            <span className="indicator-label">RSI</span>
            <span className={`indicator-value mono ${latest.rsi_rising ? 'price-up' : 'price-down'}`}>
              {latest.rsi?.toFixed(1)} {latest.rsi_rising ? '↑' : '↓'}
            </span>
          </div>

          <div className="indicator-pill">
            <span className="indicator-label">MACD</span>
            <span className={`indicator-value ${latest.macd_crossover === 'bullish' ? 'price-up' : latest.macd_crossover === 'bearish' ? 'price-down' : 'price-neutral'}`}>
              {latest.macd_crossover === 'bullish' ? '✦ Bull Cross' : latest.macd_crossover === 'bearish' ? '✦ Bear Cross' : 'Neutral'}
            </span>
          </div>
        </div>
      )}

      {/* Main Price Chart */}
      <PriceChart candles={candles} indicators={indicators} mode={mode} />

      {/* Sub-panels */}
      <RSIPanel data={indicators?.rsi} />
      <MACDPanel
        macdLine={indicators?.macd_line}
        macdSignal={indicators?.macd_signal}
        macdHistogram={indicators?.macd_histogram}
      />
    </div>
  );
}
