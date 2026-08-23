/**
 * JournalPage — Paper Trading Journal view.
 *
 * Displays a filterable table of all paper trades with:
 * - Expandable rows showing the indicator snapshot at entry
 * - Inline close-trade form with exit price input
 * - Reflection notes textarea with save button
 * - Summary stats bar (total trades, open, net PnL, win rate)
 */

import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Clock,
  Target,
  DollarSign,
  Activity,
  Save,
  X,
  Edit2,
  Trash2,
} from 'lucide-react';
import { paperTradeApi } from '../api/client';
import '../components/PaperTrade/PaperTrade.css';

// ── Helpers ───────────────────────────────────────────────────────────────────

const directionConfig = {
  INTRADAY_BUY: { label: 'Intraday Buy', badge: 'dir-buy', icon: TrendingUp },
  SHORT_SELL:   { label: 'Short Sell',   badge: 'dir-short', icon: TrendingDown },
  LONG_TERM:    { label: 'Long-Term',    badge: 'dir-long',  icon: Clock },
};

function fmt(num, decimals = 2) {
  if (num == null) return '—';
  return Number(num).toFixed(decimals);
}

function fmtDate(iso) {
  if (!iso) return '—';
  const utcIso = iso.endsWith('Z') ? iso : `${iso}Z`;
  return new Date(utcIso).toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

function PnLDisplay({ value }) {
  if (value == null) return <span className="pnl-neutral">—</span>;
  const cls = value >= 0 ? 'pnl-positive' : 'pnl-negative';
  return (
    <span className={cls}>
      {value >= 0 ? '+' : ''}₹{fmt(value)}
    </span>
  );
}

// ── Expanded Row ──────────────────────────────────────────────────────────────

function ExpandedRow({ trade, colSpan, onClosed }) {
  const queryClient = useQueryClient();
  const [exitPrice, setExitPrice] = useState('');
  const [notes, setNotes] = useState(trade.reflection_notes ?? '');
  const [notesSaved, setNotesSaved] = useState(false);

  const [isEditing, setIsEditing] = useState(false);
  const [editPrice, setEditPrice] = useState(trade.entry_price);
  const [editQty, setEditQty] = useState(trade.quantity);
  const [editDir, setEditDir] = useState(trade.trade_direction);
  const [editSL, setEditSL] = useState(trade.user_defined_stop_loss || '');

  const closeMutation = useMutation({
    mutationFn: ({ id, price }) => paperTradeApi.close(id, price),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-trades'] });
      if (onClosed) onClosed();
    },
  });

  const notesMutation = useMutation({
    mutationFn: ({ id, notes: n }) => paperTradeApi.updateNotes(id, n),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-trades'] });
      setNotesSaved(true);
      setTimeout(() => setNotesSaved(false), 2000);
    },
  });

  const editMutation = useMutation({
    mutationFn: (data) => paperTradeApi.edit(trade.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-trades'] });
      setIsEditing(false);
    },
  });

  const removeMutation = useMutation({
    mutationFn: () => paperTradeApi.remove(trade.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-trades'] });
      if (onClosed) onClosed();
    },
  });

  const isLongTerm = trade.trade_direction === 'LONG_TERM';

  // Conditionally show weekly (Long-Term) or intraday indicator pills
  const indicators = isLongTerm
    ? [
        { label: '200-W SMA',      value: trade.indicator_snapshot_weekly_sma_200 != null ? `₹${fmt(trade.indicator_snapshot_weekly_sma_200)}` : '—', highlight: 'blue' },
        { label: 'Weekly RSI (14)', value: trade.indicator_snapshot_weekly_rsi != null ? fmt(trade.indicator_snapshot_weekly_rsi, 1) : '—', highlight: trade.indicator_snapshot_weekly_rsi <= 42 ? 'green' : 'default' },
        { label: 'Weekly MACD',    value: trade.indicator_snapshot_weekly_macd != null ? fmt(trade.indicator_snapshot_weekly_macd, 4) : '—' },
        { label: 'Weekly BB Lower', value: trade.indicator_snapshot_weekly_bb_lower != null ? `₹${fmt(trade.indicator_snapshot_weekly_bb_lower)}` : '—', highlight: 'amber' },
        { label: 'MACD Signal',    value: fmt(trade.indicator_snapshot_macd_signal, 4) },
        { label: 'Snapshot',       value: fmtDate(trade.entry_time) },
      ]
    : [
        { label: 'RSI (14)',      value: fmt(trade.indicator_snapshot_rsi, 1) },
        { label: 'MACD Line',    value: fmt(trade.indicator_snapshot_macd_fast, 4) },
        { label: 'MACD Signal',  value: fmt(trade.indicator_snapshot_macd_signal, 4) },
        { label: 'VWAP',         value: trade.indicator_snapshot_vwap != null ? `₹${fmt(trade.indicator_snapshot_vwap)}` : '—' },
        { label: 'Supertrend',   value: `₹${fmt(trade.indicator_snapshot_supertrend)}` },
        { label: 'Snapshot',     value: fmtDate(trade.entry_time) },
      ];

  return (
    <tr className="journal-expand-panel">
      <td colSpan={colSpan} style={{ padding: 0, border: 'none' }}>
        <div className="journal-expand-inner">
          {/* Left: Indicator snapshot */}
          <div>
            <div className="journal-notes-label" style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between' }}>
              <div>
                <Activity size={12} /> Indicator Snapshot at Entry
                {trade.is_manual_override && (
                  <span className="badge badge-amber" style={{ marginLeft: 8 }}>
                    Manual Override
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className="btn btn-sm btn-icon"
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)' }}
                  onClick={() => setIsEditing(!isEditing)}
                  title="Edit Trade"
                >
                  <Edit2 size={14} />
                </button>
                <button
                  className="btn btn-sm btn-icon"
                  style={{ background: 'transparent', border: 'none', color: 'var(--red)' }}
                  onClick={() => {
                    if (window.confirm('Are you sure you want to permanently delete this paper trade?')) {
                      removeMutation.mutate();
                    }
                  }}
                  title="Delete Trade"
                  disabled={removeMutation.isPending}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
            {isEditing && (
              <div style={{ marginBottom: 16, padding: 12, background: 'var(--bg-subtle)', borderRadius: 8, border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: 8, color: 'var(--text-bright)' }}>Edit Trade Parameters</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
                  <div className="pt-field">
                    <label className="pt-field-label">Entry Price</label>
                    <input className="input" type="number" step="any" value={editPrice} onChange={(e) => setEditPrice(e.target.value)} />
                  </div>
                  <div className="pt-field">
                    <label className="pt-field-label">Quantity</label>
                    <input className="input" type="number" value={editQty} onChange={(e) => setEditQty(e.target.value)} />
                  </div>
                  <div className="pt-field">
                    <label className="pt-field-label">Direction</label>
                    <select className="input" value={editDir} onChange={(e) => setEditDir(e.target.value)}>
                      <option value="INTRADAY_BUY">Intraday Buy</option>
                      <option value="SHORT_SELL">Short Sell</option>
                      <option value="LONG_TERM">Long-Term</option>
                    </select>
                  </div>
                  <div className="pt-field">
                    <label className="pt-field-label">Custom Stop Loss (Optional)</label>
                    <input className="input" type="number" step="any" value={editSL} onChange={(e) => setEditSL(e.target.value)} placeholder="e.g. 150.5" />
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                  <button className="btn btn-sm" onClick={() => setIsEditing(false)}>Cancel</button>
                  <button 
                    className="btn btn-sm btn-primary"
                    disabled={editMutation.isPending}
                    onClick={() => editMutation.mutate({
                      entry_price: parseFloat(editPrice),
                      quantity: parseInt(editQty, 10),
                      trade_direction: editDir,
                      user_defined_stop_loss: editSL ? parseFloat(editSL) : null,
                    })}
                  >
                    {editMutation.isPending ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </div>
            )}
            <div className="indicator-snapshot-grid">
              {/* Section label for Long-Term weekly indicators */}
              {isLongTerm && (
                <div style={{ gridColumn: '1 / -1', fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ color: 'var(--blue)' }}>📊</span> Weekly Macro Indicators
                </div>
              )}
              {indicators.map((ind) => {
                const valueColor =
                  ind.highlight === 'green' ? 'var(--green)' :
                  ind.highlight === 'amber' ? 'var(--amber)' :
                  ind.highlight === 'blue'  ? 'var(--blue)'  :
                  undefined;
                return (
                  <div key={ind.label} className="indicator-pill">
                    <span className="indicator-pill-label">{ind.label}</span>
                    <span className="indicator-pill-value" style={valueColor ? { color: valueColor } : undefined}>
                      {ind.value}
                    </span>
                  </div>
                );
              })}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 12 }}>
              <div className="indicator-pill">
                <span className="indicator-pill-label">Break-Even</span>
                <span className="indicator-pill-value" style={{ color: 'var(--amber)' }}>
                  ₹{fmt(trade.calculated_break_even_price)}
                </span>
              </div>
              <div className="indicator-pill">
                <span className="indicator-pill-label">Stop-Loss</span>
                <span className="indicator-pill-value" style={{ color: 'var(--red)' }}>
                  ₹{fmt(trade.suggested_stop_loss_price)}
                </span>
              </div>
            </div>

            {/* Exit price — only for closed trades */}
            {trade.status === 'CLOSED' && trade.exit_price != null && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 8 }}>
                <div className="indicator-pill">
                  <span className="indicator-pill-label">Exit Price</span>
                  <span className="indicator-pill-value" style={{ color: 'var(--green)' }}>
                    ₹{fmt(trade.exit_price)}
                  </span>
                </div>
                <div className="indicator-pill">
                  <span className="indicator-pill-label">Exit Time</span>
                  <span className="indicator-pill-value">{fmtDate(trade.exit_time)}</span>
                </div>
              </div>
            )}

            {/* Close trade form — only for open trades */}
            {trade.status === 'OPEN' && (
              <div className="journal-close-form">
                <div className="pt-field">
                  <label className="pt-field-label">Exit Price (₹)</label>
                  <input
                    className="input"
                    type="number"
                    step="any"
                    min="0"
                    placeholder="Enter exit price"
                    value={exitPrice}
                    onChange={(e) => setExitPrice(e.target.value)}
                  />
                </div>
                <button
                  className="btn btn-danger"
                  style={{ marginBottom: 0 }}
                  disabled={!exitPrice || closeMutation.isPending}
                  onClick={() =>
                    closeMutation.mutate({ id: trade.id, price: parseFloat(exitPrice) })
                  }
                >
                  {closeMutation.isPending ? 'Closing…' : 'Close Trade'}
                </button>
              </div>
            )}
          </div>

          {/* Right: Reflection notes */}
          <div className="journal-notes-section">
            <div className="journal-notes-label">
              <BookOpen size={12} /> Reflection Notes
            </div>
            <textarea
              className="journal-notes-textarea"
              placeholder={
                '📝 What did you notice before entering?\n' +
                '📐 Did you follow your rules?\n' +
                '⚠️ What would you do differently?'
              }
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              {notesSaved && (
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--green)', alignSelf: 'center' }}>
                  ✓ Saved
                </span>
              )}
              <button
                className="btn btn-sm"
                style={{ background: 'var(--amber-dim)', borderColor: 'rgba(255,171,0,0.3)', color: 'var(--amber)' }}
                disabled={notesMutation.isPending}
                onClick={() => notesMutation.mutate({ id: trade.id, notes })}
              >
                <Save size={12} />
                {notesMutation.isPending ? 'Saving…' : 'Save Notes'}
              </button>
            </div>
          </div>
        </div>
      </td>
    </tr>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function JournalPage() {
  const [tab, setTab] = useState('ALL'); // ALL | OPEN | CLOSED
  const [expandedId, setExpandedId] = useState(null);
  
  // Date filters
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const { data: trades = [], isLoading } = useQuery({
    queryKey: ['paper-trades', tab],
    queryFn: () =>
      paperTradeApi
        .list(tab === 'ALL' ? {} : { status: tab })
        .then((r) => r.data),
    refetchInterval: 30000,
  });

  const filteredTrades = useMemo(() => {
    return trades.filter((t) => {
      if (!t.entry_time) return true;
      const entryTime = new Date(t.entry_time);
      if (startDate) {
        const start = new Date(startDate);
        start.setHours(0, 0, 0, 0);
        if (entryTime < start) return false;
      }
      if (endDate) {
        const end = new Date(endDate);
        end.setHours(23, 59, 59, 999);
        if (entryTime > end) return false;
      }
      return true;
    });
  }, [trades, startDate, endDate]);

  // ── Stats ─────────────────────────────────────────────────────────────────
  const stats = useMemo(() => {
    const all = filteredTrades;
    const closed = all.filter((t) => t.status === 'CLOSED');
    const open = all.filter((t) => t.status === 'OPEN');
    const totalNetPnL = closed.reduce((s, t) => s + (t.pnl_net_after_fees ?? 0), 0);
    const winners = closed.filter((t) => (t.pnl_net_after_fees ?? 0) > 0).length;
    const winRate = closed.length > 0 ? ((winners / closed.length) * 100).toFixed(0) : '—';
    return { total: all.length, open: open.length, totalNetPnL, winRate, closedCount: closed.length };
  }, [filteredTrades]);

  const toggleExpand = (id) => setExpandedId((prev) => (prev === id ? null : id));

  const COLUMNS = 10;

  return (
    <div style={{ padding: 'var(--space-lg)' }}>
      {/* Header */}
      <div className="journal-header" style={{ flexWrap: 'wrap', gap: '16px', alignItems: 'center' }}>
        <h1 className="journal-title">
          <BookOpen size={26} strokeWidth={2} />
          Paper Trading Journal
        </h1>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginLeft: 'auto' }}>
          <label style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>From:</label>
          <input 
            type="date" 
            className="input" 
            style={{ padding: '6px 10px', width: 'auto', minHeight: 'auto' }} 
            value={startDate} 
            onChange={(e) => setStartDate(e.target.value)} 
          />
          <label style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', marginLeft: '4px' }}>To:</label>
          <input 
            type="date" 
            className="input" 
            style={{ padding: '6px 10px', width: 'auto', minHeight: 'auto' }} 
            value={endDate} 
            onChange={(e) => setEndDate(e.target.value)} 
          />
          {(startDate || endDate) && (
            <button 
              className="btn" 
              style={{ padding: '6px 12px', minHeight: 'auto', fontSize: '13px' }} 
              onClick={() => { setStartDate(''); setEndDate(''); }}
            >
              Clear
            </button>
          )}
        </div>

        {/* Tabs */}
        <div className="journal-tabs" style={{ marginLeft: '0' }}>
          {['ALL', 'OPEN', 'CLOSED'].map((t) => (
            <button
              key={t}
              className={`journal-tab ${tab === t ? 'active' : ''}`}
              onClick={() => { setTab(t); setExpandedId(null); }}
            >
              {t === 'ALL' ? 'All Trades' : t === 'OPEN' ? `Open (${stats.open})` : `Closed (${stats.closedCount})`}
            </button>
          ))}
        </div>
      </div>

      {/* Stats bar */}
      <div className="journal-stats">
        <div className="journal-stat-card">
          <span className="journal-stat-label"><Activity size={11} style={{ marginRight: 4 }} />Total Trades</span>
          <span className="journal-stat-value" style={{ color: 'var(--text-primary)' }}>
            {stats.total}
          </span>
        </div>
        <div className="journal-stat-card">
          <span className="journal-stat-label"><Target size={11} style={{ marginRight: 4 }} />Open Positions</span>
          <span className="journal-stat-value" style={{ color: 'var(--amber)' }}>
            {stats.open}
          </span>
        </div>
        <div className="journal-stat-card">
          <span className="journal-stat-label"><DollarSign size={11} style={{ marginRight: 4 }} />Net PnL (Closed)</span>
          <span
            className="journal-stat-value"
            style={{ color: stats.totalNetPnL >= 0 ? 'var(--green)' : 'var(--red)' }}
          >
            {stats.closedCount > 0
              ? `${stats.totalNetPnL >= 0 ? '+' : ''}₹${Math.abs(stats.totalNetPnL).toFixed(2)}`
              : '—'}
          </span>
        </div>
        <div className="journal-stat-card">
          <span className="journal-stat-label"><TrendingUp size={11} style={{ marginRight: 4 }} />Win Rate</span>
          <span
            className="journal-stat-value"
            style={{ color: 'var(--text-primary)' }}
          >
            {stats.winRate}{stats.winRate !== '—' ? '%' : ''}
          </span>
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="empty-state glass-card" style={{ padding: 48 }}>
          <div style={{ width: 32, height: 32, border: '3px solid var(--border)', borderTopColor: 'var(--blue)', borderRadius: '50%', animation: 'pt-spin 0.7s linear infinite' }} />
          <p>Loading journal…</p>
        </div>
      ) : filteredTrades.length === 0 ? (
        <div className="empty-state glass-card" style={{ padding: 56 }}>
          <BookOpen size={40} strokeWidth={1.2} />
          <p style={{ fontSize: 'var(--text-lg)', fontWeight: 600 }}>No trades found</p>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', maxWidth: 340, textAlign: 'center' }}>
            {trades.length === 0 
              ? "Click the 📝 Paper Trade button on any watchlist stock to log your first educational trade." 
              : "Try adjusting your date filters."}
          </p>
        </div>
      ) : (
        <div className="journal-table-wrapper">
          <table className="journal-table">
            <thead>
              <tr>
                <th></th>
                <th>Ticker</th>
                <th>Direction</th>
                <th>Qty</th>
                <th>Entry ₹</th>
                <th>Exit ₹</th>
                <th>Break-Even ₹</th>
                <th>SL ₹</th>
                <th>Net PnL</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredTrades.map((trade) => {
                const dcfg = directionConfig[trade.trade_direction] ?? {};
                const isExpanded = expandedId === trade.id;
                const DirIcon = dcfg.icon ?? Activity;

                return (
                  <React.Fragment key={trade.id}>
                    <tr
                      className={isExpanded ? 'journal-row-expanded' : ''}
                      style={{ cursor: 'pointer' }}
                      onClick={() => toggleExpand(trade.id)}
                    >
                      <td style={{ width: 32, paddingRight: 0 }}>
                        <button className={`expand-toggle ${isExpanded ? 'open' : ''}`}>
                          {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                        </button>
                      </td>
                      <td>
                        <span className="mono" style={{ fontWeight: 700 }}>{trade.ticker}</span>
                        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                          {fmtDate(trade.entry_time)}
                        </div>
                      </td>
                      <td>
                        <span className={`badge ${dcfg.badge ?? ''}`}>
                          <DirIcon size={10} />
                          {dcfg.label ?? trade.trade_direction}
                        </span>
                      </td>
                      <td className="mono">{trade.quantity}</td>
                      <td className="mono">₹{fmt(trade.entry_price)}</td>
                      <td className="mono" style={{ color: trade.exit_price != null ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                        {trade.exit_price != null ? `₹${fmt(trade.exit_price)}` : '—'}
                      </td>
                      <td className="mono" style={{ color: 'var(--amber)' }}>
                        ₹{fmt(trade.calculated_break_even_price)}
                      </td>
                      <td className="mono" style={{ color: 'var(--red)' }}>
                        ₹{fmt(trade.suggested_stop_loss_price)}
                      </td>
                      <td>
                        <PnLDisplay value={trade.pnl_net_after_fees} />
                        {trade.pnl_gross != null && (
                          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                            gross ₹{fmt(trade.pnl_gross)}
                          </div>
                        )}
                      </td>
                      <td>
                        <span className={`badge ${trade.status === 'OPEN' ? 'status-open' : 'status-closed'}`}>
                          {trade.status}
                        </span>
                      </td>
                    </tr>

                    {isExpanded && (
                      <ExpandedRow
                        trade={trade}
                        colSpan={COLUMNS}
                        onClosed={() => setExpandedId(null)}
                      />
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
