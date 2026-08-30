import { useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import ChartContainer from '../components/Chart/ChartContainer';
import { marketApi } from '../api/client';
import '../components/Chart/Chart.css';

const INTERVALS = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '1h', label: '1H' },
  { value: '1d', label: '1D' },
  { value: '1wk', label: '1W' },
];

const INTERVAL_PERIOD_MAP = {
  '1m': '1d',
  '5m': '5d',
  '15m': '5d',
  '1h': '1mo',
  '1d': '1y',
  '1wk': '2y',
};

const INTERVAL_MODE_MAP = {
  '1m': 'intraday',
  '5m': 'intraday',
  '15m': 'intraday',
  '1h': 'intraday',
  '1d': 'long_term',
  '1wk': 'long_term',
};

const MODE_DEFAULT_INTERVAL_MAP = {
  intraday: '5m',
  long_term: '1d',
};

export default function ChartPage() {
  const { ticker } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const initialMode = searchParams.get('mode') || 'intraday';
  const initialInterval = MODE_DEFAULT_INTERVAL_MAP[initialMode] || '5m';

  const [interval, setInterval] = useState(initialInterval);
  const [mode, setMode] = useState(initialMode);

  const handleIntervalChange = (newInterval) => {
    setInterval(newInterval);
    const impliedMode = INTERVAL_MODE_MAP[newInterval];
    setMode(impliedMode || 'intraday');
  };

  const period = INTERVAL_PERIOD_MAP[interval] || '5d';

  const { data: chartData, isLoading, refetch } = useQuery({
    queryKey: ['chart', ticker, interval],
    queryFn: () =>
      marketApi.getChart(ticker, interval, period, mode).then((r) => r.data),
    refetchInterval: interval === '1d' || interval === '1wk' ? 300000 : 60000,
  });

  const { data: indicatorData } = useQuery({
    queryKey: ['indicators', ticker, mode],
    queryFn: () => marketApi.getIndicators(ticker, mode).then((r) => r.data),
    refetchInterval: 60000,
  });

  const confluence = indicatorData?.confluence;

  return (
    <div className="chart-page">
      {/* Header */}
      <div className="chart-page-header">
        <div className="chart-page-ticker">
          <button className="btn btn-ghost btn-icon" onClick={() => navigate('/')}>
            <ArrowLeft size={18} />
          </button>
          <span className="chart-page-symbol">{ticker?.toUpperCase()}</span>
          {chartData?.latest?.price && (
            <span className="chart-page-price">
              ₹{chartData.latest.price.toFixed(2)}
            </span>
          )}
        </div>

        <div className="chart-page-controls">
          {/* Interval selector */}
          {INTERVALS.map((iv) => (
            <button
              key={iv.value}
              className={`chart-interval-btn ${interval === iv.value ? 'active' : ''}`}
              onClick={() => handleIntervalChange(iv.value)}
            >
              {iv.label}
            </button>
          ))}

          <button
            className="btn btn-ghost btn-icon"
            onClick={() => refetch()}
            title="Refresh"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-pulse' : ''} />
          </button>
        </div>
      </div>

      {/* Confluence Status */}
      {confluence && (
        <div 
          className={`confluence-card ${confluence.is_aligned ? 'confluence-card-aligned' : ''}`}
          style={{
            borderColor: confluence.signal === 'BUY' ? 'var(--green)' : confluence.signal === 'SELL' ? 'var(--red)' : 'var(--border)',
            backgroundColor: confluence.signal === 'BUY' ? 'rgba(0, 230, 118, 0.05)' : confluence.signal === 'SELL' ? 'rgba(255, 23, 68, 0.05)' : 'var(--bg-card)'
          }}
        >
          <div className="confluence-header">
            <span style={{ fontSize: 20 }}>
              {confluence.is_aligned ? '🎯' : '⏳'}
            </span>
            <span className="confluence-title" style={{ color: confluence.signal === 'BUY' ? 'var(--green)' : confluence.signal === 'SELL' ? 'var(--red)' : 'inherit' }}>
              {confluence.is_aligned
                ? `All 4 Indicators Aligned (${confluence.signal})`
                : 'Waiting for Confluence'}
            </span>
            <span className={`badge ${mode === 'long_term' ? 'badge-blue' : 'badge-amber'}`}>
              {mode.replace('_', ' ')}
            </span>
          </div>

          <div className="confluence-checks">
            {Object.entries(confluence.checks || {}).map(([key, passed]) => (
              <div key={key} className="confluence-check">
                <div className={`confluence-check-icon ${passed ? 'confluence-check-pass' : 'confluence-check-fail'}`}>
                  {passed ? '✓' : '✗'}
                </div>
                <span>
                  <strong style={{ textTransform: 'uppercase' }}>{key}</strong>
                  {confluence.details?.[key] && (
                    <span style={{ display: 'block', color: 'var(--text-muted)', fontSize: 10 }}>
                      {confluence.details[key]}
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Chart */}
      {isLoading ? (
        <div className="chart-wrapper">
          <div className="skeleton" style={{ height: 420 }} />
          <div className="skeleton" style={{ height: 140, marginTop: 2 }} />
          <div className="skeleton" style={{ height: 140, marginTop: 2 }} />
        </div>
      ) : (
        <ChartContainer chartData={chartData} mode={mode} />
      )}
    </div>
  );
}
