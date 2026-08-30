import { useQuery } from '@tanstack/react-query';
import { Bell, Target } from 'lucide-react';
import WatchlistPanel from '../components/Watchlist/WatchlistPanel';
import { alertsApi } from '../api/client';
import '../components/Watchlist/Watchlist.css';

export default function DashboardPage() {
  const { data: alerts = [] } = useQuery({
    queryKey: ['alerts', 'recent'],
    queryFn: () => alertsApi.list({ limit: 5 }).then((r) => r.data),
    refetchInterval: 30000,
  });

  return (
    <div>
      {/* 2-column watchlist grid */}
      <div className="dashboard-grid">
        <WatchlistPanel mode="intraday" />
        <WatchlistPanel mode="long_term" />
      </div>

      {/* Recent Alerts */}
      <div className="alert-feed">
        <div className="alert-feed-header">
          <h2 className="alert-feed-title">
            <Bell size={18} style={{ marginRight: 8, verticalAlign: 'middle' }} />
            Recent Alerts
          </h2>
        </div>

        {alerts.length === 0 ? (
          <div className="empty-state glass-card" style={{ padding: 32 }}>
            <Target size={36} strokeWidth={1.5} />
            <p>No confluence alerts yet</p>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
              Add stocks to your watchlists — the scanner will notify you when all indicators align
            </p>
          </div>
        ) : (
          alerts.map((alert, i) => (
            <div
              key={alert.id}
              className="alert-card"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <div
                className="alert-card-icon"
                style={{
                  background: alert.alert_type?.includes('bullish')
                    ? 'var(--green-dim)'
                    : 'var(--red-dim)',
                }}
              >
                {alert.alert_type?.includes('bullish') ? '📈' : '📉'}
              </div>
              <div className="alert-card-content">
                <div className="alert-card-title">
                  <span className="mono" style={{ marginRight: 8 }}>{alert.ticker}</span>
                  <span className={`badge ${alert.mode === 'long_term' ? 'badge-blue' : 'badge-green'}`}>
                    {alert.mode?.replace('_', ' ')}
                  </span>
                </div>
                <div className="alert-card-detail">
                  Price at alert: <strong className="mono">₹{alert.price_at_alert?.toFixed(2)}</strong>
                  {alert.indicator_data?.rsi && (
                    <> · RSI: {alert.indicator_data.rsi.toFixed(1)}</>
                  )}
                </div>
              </div>
              <div className="alert-card-time">
                {new Date(alert.created_at.endsWith('Z') ? alert.created_at : `${alert.created_at}Z`).toLocaleString('en-IN', {
                  timeZone: 'Asia/Kolkata',
                  day: 'numeric',
                  month: 'short',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
