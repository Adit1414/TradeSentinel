import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, Filter, Settings, Send, Target } from 'lucide-react';
import { alertsApi } from '../api/client';
import '../components/Watchlist/Watchlist.css';
import './Pages.css';

const MODE_FILTERS = [
  { value: '', label: 'All Modes' },
  { value: 'intraday', label: 'Intraday' },
  { value: 'long_term', label: 'Long-Term' },
];

export default function AlertsPage() {
  const [modeFilter, setModeFilter] = useState('');
  const [showSettings, setShowSettings] = useState(false);

  const { data: alerts = [], isLoading } = useQuery({
    queryKey: ['alerts', modeFilter],
    queryFn: () =>
      alertsApi.list({ mode: modeFilter || undefined, limit: 100 }).then((r) => r.data),
    refetchInterval: 30000,
  });

  const { data: alertCount } = useQuery({
    queryKey: ['alerts-count'],
    queryFn: () => alertsApi.count().then((r) => r.data),
  });

  return (
    <div className="alerts-page">
      <div className="page-header">
        <div>
          <h2 style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>
            Alert History
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>
            {alertCount?.count || 0} total confluence alerts triggered
          </p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
          <div style={{ display: 'flex', gap: 2 }}>
            {MODE_FILTERS.map((f) => (
              <button
                key={f.value}
                className={`chart-interval-btn ${modeFilter === f.value ? 'active' : ''}`}
                onClick={() => setModeFilter(f.value)}
              >
                {f.label}
              </button>
            ))}
          </div>
          <button className="btn" onClick={() => setShowSettings(true)}>
            <Settings size={14} />
            Settings
          </button>
        </div>
      </div>

      <div style={{ marginTop: 'var(--space-lg)' }}>
        {isLoading ? (
          <div>
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="skeleton" style={{ height: 64, marginBottom: 8, borderRadius: 10 }} />
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div className="empty-state glass-card" style={{ padding: 48 }}>
            <Target size={42} strokeWidth={1.5} />
            <p style={{ fontSize: 'var(--text-base)' }}>No alerts found</p>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', maxWidth: 320 }}>
              {modeFilter
                ? `No confluence alerts for ${modeFilter.replace('_', ' ')} mode`
                : 'The scanner will alert you when all 4 indicators align for any watchlist stock'}
            </p>
          </div>
        ) : (
          alerts.map((alert, i) => (
            <div
              key={alert.id}
              className="alert-card"
              style={{ animationDelay: `${i * 40}ms` }}
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
                  <span className="mono" style={{ marginRight: 8, fontSize: 'var(--text-base)' }}>
                    {alert.ticker}
                  </span>
                  <span className={`badge ${
                    alert.mode === 'long_term' ? 'badge-blue' : 'badge-green'
                  }`}>
                    {alert.mode?.replace('_', ' ')}
                  </span>
                  {alert.notified_via && (
                    <span className="badge badge-purple" style={{ marginLeft: 4 }}>
                      {alert.notified_via}
                    </span>
                  )}
                </div>
                <div className="alert-card-detail">
                  Price: <strong className="mono">₹{alert.price_at_alert?.toFixed(2)}</strong>
                  {alert.indicator_data && (
                    <>
                      {alert.indicator_data.rsi != null && (
                        <> · RSI: <span className="mono">{alert.indicator_data.rsi.toFixed(1)}</span></>
                      )}
                      {alert.indicator_data.macd != null && (
                        <> · MACD: <span className="mono">{alert.indicator_data.macd.toFixed(4)}</span></>
                      )}
                      {alert.indicator_data.supertrend_dir != null && (
                        <> · ST: {alert.indicator_data.supertrend_dir === 1 ? '▲ Bullish' : '▼ Bearish'}</>
                      )}
                    </>
                  )}
                </div>
              </div>
              <div className="alert-card-time">
                {new Date(alert.created_at.endsWith('Z') ? alert.created_at : `${alert.created_at}Z`).toLocaleString('en-IN', {
                  timeZone: 'Asia/Kolkata',
                  day: 'numeric',
                  month: 'short',
                  year: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>
          ))
        )}
      </div>

      {showSettings && <AlertSettingsModal onClose={() => setShowSettings(false)} />}
    </div>
  );
}

/* ── Alert Settings Modal ──────────────────────────────────────────── */
function AlertSettingsModal({ onClose }) {
  const queryClient = useQueryClient();
  const [ntfyTopic, setNtfyTopic] = useState('');
  const [botToken, setBotToken] = useState('');
  const [chatId, setChatId] = useState('');

  const [discordWebhookUrl, setDiscordWebhookUrl] = useState('');

  const { data: settings } = useQuery({
    queryKey: ['alert-settings'],
    queryFn: () => alertsApi.getSettings().then((r) => {
      if (r.data.ntfy_topic) setNtfyTopic(r.data.ntfy_topic);
      if (r.data.discord_webhook_url) setDiscordWebhookUrl(r.data.discord_webhook_url);
      if (r.data.telegram_bot_token) setBotToken(r.data.telegram_bot_token);
      if (r.data.telegram_chat_id) setChatId(r.data.telegram_chat_id);
      return r.data;
    }),
  });

  const saveMutation = useMutation({
    mutationFn: (data) => alertsApi.updateSettings(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alert-settings'] }),
  });

  const testNtfyMutation = useMutation({
    mutationFn: (topic) => alertsApi.testNtfy(topic),
  });

  const testDiscordMutation = useMutation({
    mutationFn: (webhook_url) => alertsApi.testDiscord(webhook_url),
  });

  const testTelegramMutation = useMutation({
    mutationFn: (data) => alertsApi.testTelegram(data),
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 480 }}>
        <div className="modal-header">
          <h2 className="modal-title">Notification Settings</h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Ntfy section */}
        <div style={{ marginBottom: 'var(--space-lg)', paddingBottom: 'var(--space-md)', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: '1.1rem' }}>🔔</span>
            <strong style={{ fontSize: 'var(--text-sm)', color: 'var(--text-bright)' }}>Ntfy.sh (Recommended — 100% Anonymous)</strong>
          </div>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 12 }}>
            Subscribe to a topic in the Ntfy mobile app or browser. No sign-up required.
          </p>
          <label className="label">Secret Topic Name</label>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              className="input"
              value={ntfyTopic}
              onChange={(e) => setNtfyTopic(e.target.value)}
              placeholder="e.g. aditya-trading-alerts-778899"
            />
            <button
              className="btn"
              onClick={() => testNtfyMutation.mutate(ntfyTopic)}
              disabled={testNtfyMutation.isPending || !ntfyTopic}
            >
              <Send size={14} />
              {testNtfyMutation.isPending ? 'Testing...' : 'Test'}
            </button>
          </div>
          {testNtfyMutation.isSuccess && (
            <div className="form-success" style={{ marginTop: 8 }}>
              ✅ Test push notification sent to ntfy.sh/{ntfyTopic}!
            </div>
          )}
          {testNtfyMutation.isError && (
            <div className="form-error" style={{ marginTop: 8 }}>
              ❌ {testNtfyMutation.error?.response?.data?.detail || 'Failed to send test push notification'}
            </div>
          )}
        </div>

        {/* Discord section */}
        <div style={{ marginBottom: 'var(--space-md)', paddingBottom: 'var(--space-md)', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: '1.1rem' }}>👾</span>
            <strong style={{ fontSize: 'var(--text-sm)', color: 'var(--text-bright)' }}>Discord Webhook (Highly Recommended)</strong>
          </div>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 12 }}>
            Free, anonymous, and no rate limits. Create a webhook in your Discord server settings.
          </p>
          <label className="label">Webhook URL</label>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              className="input"
              value={discordWebhookUrl}
              onChange={(e) => setDiscordWebhookUrl(e.target.value)}
              placeholder="https://discord.com/api/webhooks/..."
            />
            <button
              className="btn"
              onClick={() => testDiscordMutation.mutate(discordWebhookUrl)}
              disabled={testDiscordMutation.isPending || !discordWebhookUrl}
            >
              <Send size={14} />
              {testDiscordMutation.isPending ? 'Testing...' : 'Test'}
            </button>
          </div>
          {testDiscordMutation.isSuccess && (
            <div className="form-success" style={{ marginTop: 8 }}>
              ✅ Test message sent to Discord!
            </div>
          )}
          {testDiscordMutation.isError && (
            <div className="form-error" style={{ marginTop: 8 }}>
              ❌ {testDiscordMutation.error?.response?.data?.detail || 'Failed to send test message'}
            </div>
          )}
        </div>

        {/* Telegram section */}
        <div style={{ marginBottom: 'var(--space-md)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: '1.1rem' }}>✈️</span>
            <strong style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Telegram Bot (Optional)</strong>
          </div>

          <div style={{ marginBottom: 12 }}>
            <label className="label">Bot Token</label>
            <input
              className="input"
              type="password"
              value={botToken}
              onChange={(e) => setBotToken(e.target.value)}
              placeholder="123456:ABC-DEF1234..."
            />
          </div>

          <div>
            <label className="label">Chat ID</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                className="input"
                value={chatId}
                onChange={(e) => setChatId(e.target.value)}
                placeholder="Your chat ID"
              />
              <button
                className="btn"
                onClick={() => testTelegramMutation.mutate({ telegram_bot_token: botToken, telegram_chat_id: chatId })}
                disabled={testTelegramMutation.isPending || !botToken || !chatId}
              >
                <Send size={14} />
                {testTelegramMutation.isPending ? 'Testing...' : 'Test'}
              </button>
            </div>
          </div>
          {testTelegramMutation.isSuccess && (
            <div className="form-success" style={{ marginTop: 8 }}>
              ✅ Telegram test message sent!
            </div>
          )}
          {testTelegramMutation.isError && (
            <div className="form-error" style={{ marginTop: 8 }}>
              ❌ {testTelegramMutation.error?.response?.data?.detail || 'Failed to send Telegram test message'}
            </div>
          )}
        </div>

        <div className="modal-actions" style={{ marginTop: 'var(--space-lg)' }}>
          <button
            className="btn btn-primary"
            style={{ width: '100%' }}
            onClick={() =>
              saveMutation.mutate({
                ntfy_topic: ntfyTopic,
                discord_webhook_url: discordWebhookUrl,
                telegram_bot_token: botToken,
                telegram_chat_id: chatId,
              })
            }
            disabled={saveMutation.isPending}
          >
            {saveMutation.isPending ? 'Saving...' : 'Save Notification Settings'}
          </button>
        </div>

        {saveMutation.isSuccess && (
          <div className="form-success" style={{ marginTop: 12, textAlign: 'center' }}>
            ✅ Settings saved successfully!
          </div>
        )}
      </div>
    </div>
  );
}
