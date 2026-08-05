/**
 * PaperTradeModal — Smart trade entry modal.
 *
 * On open: auto-fetches live price + indicator snapshot from the backend.
 * All fields remain editable; override detection marks is_manual_override.
 * A live calculation panel instantly mirrors NSE fee math in-browser.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  X,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Clock,
  AlertTriangle,
  CheckCircle,
  Zap,
} from 'lucide-react';
import { paperTradeApi } from '../../api/client';
import './PaperTrade.css';

// ── NSE fee constants (mirror of backend charges.py) ──────────────────────────
const INTRADAY = {
  brokerage_pct: 0.03,
  stt_sell_pct: 0.025,
  exchange_txn_pct: 0.00297,
  stamp_duty_buy_pct: 0.003,
  gst_pct: 18,
  sebi_per_crore: 10,
};
const DELIVERY = {
  brokerage_pct: 0,
  stt_pct: 0.1,
  exchange_txn_pct: 0.00297,
  stamp_duty_buy_pct: 0.015,
  gst_pct: 18,
  sebi_per_crore: 10,
};

function calcCharges(turnover, side, isDelivery) {
  const c = isDelivery ? DELIVERY : INTRADAY;
  const brokerage = turnover * (c.brokerage_pct / 100);
  const stt = isDelivery
    ? turnover * (c.stt_pct / 100)
    : side === 'SELL' ? turnover * (INTRADAY.stt_sell_pct / 100) : 0;
  const exchange_txn = turnover * (c.exchange_txn_pct / 100);
  const stamp_duty = side === 'BUY' ? turnover * (c.stamp_duty_buy_pct / 100) : 0;
  const gst = (brokerage + exchange_txn) * (c.gst_pct / 100);
  const sebi_fee = turnover * (c.sebi_per_crore / 1e7);
  return brokerage + stt + exchange_txn + stamp_duty + gst + sebi_fee;
}

function computeLive(direction, entryPrice, qty, vwap, supertrend, ema200) {
  const price = parseFloat(entryPrice) || 0;
  const quantity = parseInt(qty, 10) || 0;
  if (price <= 0 || quantity <= 0) return null;

  const turnover = price * quantity;
  const isDelivery = direction === 'LONG_TERM';

  let entryFees, exitFees, breakEven, suggestedSL;

  if (direction === 'INTRADAY_BUY') {
    entryFees = calcCharges(turnover, 'BUY', false);
    exitFees  = calcCharges(turnover, 'SELL', false);
    breakEven = price + (entryFees + exitFees) / quantity;
    const v = parseFloat(vwap);
    suggestedSL = v > 0 ? v : price * 0.995;

  } else if (direction === 'SHORT_SELL') {
    entryFees = calcCharges(turnover, 'SELL', false);
    exitFees  = calcCharges(turnover, 'BUY', false);
    breakEven = price - (entryFees + exitFees) / quantity;
    const v = parseFloat(vwap), st = parseFloat(supertrend);
    suggestedSL = v > 0 && v > price ? v : st > 0 ? st : price * 1.005;

  } else { // LONG_TERM
    entryFees = calcCharges(turnover, 'BUY', true);
    exitFees  = calcCharges(turnover, 'SELL', true);
    breakEven = price + (entryFees + exitFees) / quantity;
    const e = parseFloat(ema200);
    suggestedSL = e > 0 ? e : price * 0.98;
  }

  return {
    breakEven: breakEven.toFixed(2),
    suggestedSL: suggestedSL.toFixed(2),
    totalFees: (entryFees + exitFees).toFixed(2),
    entryFees: entryFees.toFixed(2),
    exitFees: exitFees.toFixed(2),
  };
}

// ── Direction config ──────────────────────────────────────────────────────────
const DIRECTION_CONFIG = {
  INTRADAY_BUY: {
    label: 'Intraday Buy',
    sublabel: 'MIS · Long',
    icon: TrendingUp,
    activeClass: 'active-buy',
    badge: 'dir-buy',
    mode: 'intraday',
  },
  SHORT_SELL: {
    label: 'Short Sell',
    sublabel: 'MIS · Short',
    icon: TrendingDown,
    activeClass: 'active-short',
    badge: 'dir-short',
    mode: 'short_selling',
  },
  LONG_TERM: {
    label: 'Long-Term',
    sublabel: 'CNC · Delivery',
    icon: Clock,
    activeClass: 'active-long',
    badge: 'dir-long',
    mode: 'long_term',
  },
};

const MODE_TO_DIRECTION = {
  intraday: 'INTRADAY_BUY',
  short_selling: 'SHORT_SELL',
  long_term: 'LONG_TERM',
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function PaperTradeModal({ ticker, initialMode = 'intraday', onClose }) {
  const queryClient = useQueryClient();

  // Direction
  const [direction, setDirection] = useState(
    MODE_TO_DIRECTION[initialMode] ?? 'INTRADAY_BUY'
  );

  // Form fields
  const [fields, setFields] = useState({
    price: '',
    quantity: '1',
    rsi: '',
    macdFast: '',
    macdSignal: '',
    vwap: '',
    supertrend: '',
    ema200: '',
    // Weekly long-term fields
    weeklySma200: '',
    weeklyRsi: '',
    weeklyMacd: '',
    weeklyBbLower: '',
  });

  // Track which fields came from auto-fetch (to detect overrides)
  const autoFetched = useRef({});
  const [overriddenFields, setOverriddenFields] = useState(new Set());

  // Fetch state
  const [fetching, setFetching] = useState(false);
  const [fetchError, setFetchError] = useState('');
  const [fetchTime, setFetchTime] = useState('');

  // Live calc
  const [liveCalc, setLiveCalc] = useState(null);

  // ── Auto-fetch on mount / direction change ──────────────────────────────────
  const doFetch = useCallback(async () => {
    const cfg = DIRECTION_CONFIG[direction];
    setFetching(true);
    setFetchError('');
    try {
      const { data } = await paperTradeApi.snapshot(ticker, cfg.mode);

      let fetched;
      if (direction === 'LONG_TERM') {
        // Map weekly indicator fields from the snapshot
        fetched = {
          price:        String(data.price ?? ''),
          rsi:          String(data.rsi ?? ''),
          macdFast:     String(data.macd_fast ?? ''),
          macdSignal:   String(data.macd_signal ?? ''),
          vwap:         '',
          supertrend:   '',
          ema200:       '',
          weeklySma200: String(data.weekly_sma_200 ?? ''),
          weeklyRsi:    String(data.weekly_rsi ?? ''),
          weeklyMacd:   String(data.weekly_macd_line ?? ''),
          weeklyBbLower: String(data.weekly_bb_lower ?? ''),
        };
      } else {
        fetched = {
          price:       String(data.price ?? ''),
          rsi:         String(data.rsi ?? ''),
          macdFast:    String(data.macd_fast ?? ''),
          macdSignal:  String(data.macd_signal ?? ''),
          vwap:        String(data.vwap ?? ''),
          supertrend:  String(data.supertrend ?? ''),
          ema200:      String(data.ema_200 ?? ''),
          weeklySma200: '',
          weeklyRsi:   '',
          weeklyMacd:  '',
          weeklyBbLower: '',
        };
      }

      autoFetched.current = fetched;
      setFields((prev) => ({ ...prev, ...fetched }));
      setOverriddenFields(new Set());
      setFetchTime(new Date().toLocaleTimeString('en-IN'));
    } catch (err) {
      const detail = err?.response?.data?.detail ?? 'Could not fetch data. Enter values manually.';
      setFetchError(detail);
    } finally {
      setFetching(false);
    }
  }, [ticker, direction]);

  useEffect(() => { doFetch(); }, [doFetch]);

  // ── Live calculation ────────────────────────────────────────────────────────
  useEffect(() => {
    const result = computeLive(
      direction,
      fields.price,
      fields.quantity,
      fields.vwap,
      fields.supertrend,
      // For LONG_TERM: use the weekly 200-SMA as the SL anchor
      direction === 'LONG_TERM' ? fields.weeklySma200 : fields.ema200,
    );
    setLiveCalc(result);
  }, [direction, fields]);

  // ── Field change handler ────────────────────────────────────────────────────
  const handleChange = (key, value) => {
    setFields((prev) => ({ ...prev, [key]: value }));
    // Mark as overridden if different from auto-fetched
    if (autoFetched.current[key] !== undefined && value !== autoFetched.current[key]) {
      setOverriddenFields((prev) => new Set([...prev, key]));
    } else {
      setOverriddenFields((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  };

  // ── Submit ──────────────────────────────────────────────────────────────────
  const openMutation = useMutation({
    mutationFn: (data) => paperTradeApi.open(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-trades'] });
      onClose();
    },
  });

  const handleConfirm = () => {
    if (!fields.price || !fields.quantity) return;

    const isLongTerm = direction === 'LONG_TERM';

    openMutation.mutate({
      ticker,
      trade_direction: direction,
      quantity: parseInt(fields.quantity, 10),
      entry_price: parseFloat(fields.price),
      snapshot_rsi: parseFloat(fields.rsi) || 0,
      snapshot_macd_fast: parseFloat(fields.macdFast) || 0,
      snapshot_macd_signal: parseFloat(fields.macdSignal) || 0,
      snapshot_vwap: isLongTerm ? null : (parseFloat(fields.vwap) || null),
      snapshot_supertrend: isLongTerm ? 0 : (parseFloat(fields.supertrend) || 0),
      snapshot_ema_200: isLongTerm ? null : (parseFloat(fields.ema200) || null),
      // Weekly long-term indicator snapshot
      snapshot_weekly_sma_200: isLongTerm ? (parseFloat(fields.weeklySma200) || null) : null,
      snapshot_weekly_rsi: isLongTerm ? (parseFloat(fields.weeklyRsi) || null) : null,
      snapshot_weekly_macd: isLongTerm ? (parseFloat(fields.weeklyMacd) || null) : null,
      snapshot_weekly_bb_lower: isLongTerm ? (parseFloat(fields.weeklyBbLower) || null) : null,
      is_manual_override: overriddenFields.size > 0,
    });
  };

  // ── Field renderer helpers ──────────────────────────────────────────────────
  const renderField = (key, label, placeholder = '—') => {
    const isAuto = autoFetched.current[key] !== undefined && !fetching;
    const isOverridden = overriddenFields.has(key);

    return (
      <div className="pt-field">
        <label className="pt-field-label">
          {label}
          {isAuto && !isOverridden && (
            <span className="pt-auto-badge">
              <Zap size={8} /> AUTO
            </span>
          )}
          {isOverridden && (
            <span className="pt-auto-badge pt-override-badge">
              ✎ EDITED
            </span>
          )}
        </label>
        <input
          className="input"
          type="number"
          step="any"
          placeholder={fetching ? 'Fetching…' : placeholder}
          value={fields[key]}
          onChange={(e) => handleChange(key, e.target.value)}
          disabled={fetching}
        />
      </div>
    );
  };

  const cfg = DIRECTION_CONFIG[direction];

  return createPortal(
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-content pt-modal">

        {/* ── Fixed Header ── */}
        <div style={{ padding: 'var(--space-lg)', paddingBottom: 0, flexShrink: 0 }}>
          <div className="modal-header" style={{ marginBottom: fetchError ? 'var(--space-md)' : 'var(--space-sm)' }}>
            <div className="pt-modal-ticker">
              <span className="pt-modal-ticker-name">{ticker}</span>
              <span className={`badge ${cfg.badge}`}>{cfg.label}</span>
              {fetchTime && (
                <span className="pt-modal-time">Snapped at {fetchTime}</span>
              )}
            </div>
            <button className="btn btn-ghost btn-icon" onClick={onClose}>
              <X size={18} />
            </button>
          </div>

          {fetchError && (
            <div className="pt-fetch-error" style={{ marginBottom: 'var(--space-sm)' }}>
              <AlertTriangle size={14} />
              {fetchError}
            </div>
          )}
        </div>

        {/* ── Scrollable Body ── */}
        <div className="pt-modal-body">

          {/* Direction selector */}
          <div className="pt-direction-group">
            {Object.entries(DIRECTION_CONFIG).map(([key, dcfg]) => {
              const DirIcon = dcfg.icon;
              return (
                <button
                  key={key}
                  className={`pt-direction-btn ${direction === key ? dcfg.activeClass : ''}`}
                  onClick={() => setDirection(key)}
                >
                  <DirIcon size={16} />
                  <span>{dcfg.label}</span>
                  <span style={{ fontSize: '9px', opacity: 0.7 }}>{dcfg.sublabel}</span>
                </button>
              );
            })}
          </div>

          {/* Fields */}
          {fetching ? (
            <div className="pt-fetching-overlay">
              <div className="pt-spinner" />
              <span>Fetching live snapshot for {ticker}…</span>
            </div>
          ) : (
            <>
              <div className="pt-field-grid">
                {renderField('price', 'Entry Price (₹)', '0.00')}
                <div className="pt-field">
                  <label className="pt-field-label">Quantity</label>
                  <input
                    className="input"
                    type="number"
                    min="1"
                    step="1"
                    value={fields.quantity}
                    onChange={(e) => handleChange('quantity', e.target.value)}
                  />
                </div>

                {direction === 'LONG_TERM' ? (
                  // ── Weekly macro indicator fields for Long-Term ──
                  <>
                    {renderField('weeklySma200', '200-W SMA (₹)', '—')}
                    {renderField('weeklyRsi', 'Weekly RSI (14)', '—')}
                    {renderField('weeklyMacd', 'Weekly MACD Line', '—')}
                    {renderField('weeklyBbLower', 'Weekly BB Lower (₹)', '—')}
                    {renderField('macdFast', 'MACD Line (raw)', '0.0000')}
                    {renderField('macdSignal', 'MACD Signal (raw)', '0.0000')}
                  </>
                ) : (
                  // ── Intraday / Short-Sell indicator fields ──
                  <>
                    {renderField('rsi', 'RSI (14)', '0.00')}
                    {renderField('vwap', 'VWAP', '—')}
                    {renderField('macdFast', 'MACD Line', '0.0000')}
                    {renderField('macdSignal', 'MACD Signal', '0.0000')}
                    {renderField('supertrend', 'Supertrend', '0.00')}
                    {renderField('ema200', 'EMA 200', '—')}
                  </>
                )}
              </div>

              {/* Live calculation panel */}
              {liveCalc && (
                <div className="pt-calc-panel">
                  <div className="pt-calc-panel-title">⚡ Live NSE Fee Calculation</div>
                  <div className="pt-calc-grid">
                    <div className="pt-calc-item">
                      <span className="pt-calc-item-label">Break-Even</span>
                      <span className="pt-calc-item-value">₹{liveCalc.breakEven}</span>
                    </div>
                    <div className="pt-calc-item">
                      <span className="pt-calc-item-label">Suggested SL</span>
                      <span className="pt-calc-item-value sl-value">₹{liveCalc.suggestedSL}</span>
                    </div>
                    <div className="pt-calc-item">
                      <span className="pt-calc-item-label">Est. Total Fees</span>
                      <span className="pt-calc-item-value fees-value">₹{liveCalc.totalFees}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Override warning */}
              {overriddenFields.size > 0 && (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  fontSize: 'var(--text-xs)', color: 'var(--amber)',
                  padding: '8px 0',
                }}>
                  <AlertTriangle size={12} />
                  {overriddenFields.size} field{overriddenFields.size > 1 ? 's' : ''} manually edited —
                  trade will be flagged as <strong>&nbsp;MANUAL OVERRIDE</strong>
                </div>
              )}
            </>
          )}
        </div>

        {/* ── Fixed Footer ── */}
        <div className="pt-modal-footer">
          <button className="btn btn-ghost" onClick={doFetch} disabled={fetching}>
            <RefreshCw size={14} className={fetching ? 'animate-pulse' : ''} />
            Re-fetch
          </button>
          <button className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn btn-success"
            onClick={handleConfirm}
            disabled={fetching || !fields.price || !fields.quantity || openMutation.isPending}
          >
            {openMutation.isPending ? (
              <span className="animate-pulse">Logging…</span>
            ) : (
              <>
                <CheckCircle size={14} />
                Confirm Trade
              </>
            )}
          </button>
        </div>

        {openMutation.isError && (
          <div className="pt-fetch-error" style={{ margin: '0 var(--space-lg) var(--space-lg)' }}>
            <AlertTriangle size={14} />
            {openMutation.error?.response?.data?.detail ?? 'Failed to log trade.'}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}
