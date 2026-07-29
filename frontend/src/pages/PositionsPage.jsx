import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus, Trash2, X, Calculator, IndianRupee, TrendingUp, TrendingDown, Clock
} from 'lucide-react';
import { positionsApi } from '../api/client';
import './Pages.css';

const TRADE_TYPES = [
  { value: 'intraday', label: 'Intraday', icon: TrendingUp, color: 'green' },
  { value: 'short_selling', label: 'Short Selling', icon: TrendingDown, color: 'red' },
  { value: 'long_term', label: 'Long-Term', icon: Clock, color: 'blue' },
];

export default function PositionsPage() {
  const [showAdd, setShowAdd] = useState(false);
  const [showCalc, setShowCalc] = useState(false);
  const queryClient = useQueryClient();

  const { data: positions = [], isLoading } = useQuery({
    queryKey: ['positions'],
    queryFn: () => positionsApi.list().then((r) => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => positionsApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['positions'] }),
  });

  const closeMutation = useMutation({
    mutationFn: (id) => positionsApi.update(id, { status: 'CLOSED' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['positions'] }),
  });

  const openPositions = positions.filter((p) => p.status === 'OPEN');
  const closedPositions = positions.filter((p) => p.status === 'CLOSED');

  return (
    <div className="positions-page">
      <div className="page-header">
        <div>
          <h2 style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>
            Position Tracker
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>
            Track trades and calculate break-even exit prices
          </p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
          <button className="btn" onClick={() => setShowCalc(true)}>
            <Calculator size={14} />
            Calculator
          </button>
          <button className="btn btn-primary" onClick={() => setShowAdd(true)}>
            <Plus size={14} />
            Add Position
          </button>
        </div>
      </div>

      {/* Open Positions */}
      <div style={{ marginTop: 'var(--space-lg)' }}>
        <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 600, marginBottom: 'var(--space-sm)' }}>
          Open Positions ({openPositions.length})
        </h3>

        {openPositions.length === 0 ? (
          <div className="empty-state glass-card">
            <IndianRupee size={36} strokeWidth={1.5} />
            <p>No open positions</p>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
              Add a position to start tracking your trades
            </p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Type</th>
                  <th>Direction</th>
                  <th>Qty</th>
                  <th>Entry Price</th>
                  <th>Break-Even</th>
                  <th>Target Profit</th>
                  <th>Notes</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {openPositions.map((pos) => (
                  <tr key={pos.id}>
                    <td>
                      <span className="mono" style={{ fontWeight: 600 }}>{pos.ticker}</span>
                    </td>
                    <td>
                      <span className={`badge badge-${pos.trade_type === 'intraday' ? 'green' : pos.trade_type === 'short_selling' ? 'red' : 'blue'}`}>
                        {pos.trade_type.replace('_', ' ')}
                      </span>
                    </td>
                    <td>
                      <span className={pos.direction === 'BUY' ? 'price-up' : 'price-down'} style={{ fontWeight: 600 }}>
                        {pos.direction}
                      </span>
                    </td>
                    <td className="mono">{pos.quantity}</td>
                    <td className="mono">₹{pos.entry_price.toFixed(2)}</td>
                    <td className="mono" style={{ fontWeight: 600 }}>
                      ₹{pos.exit_price?.toFixed(2) || '—'}
                    </td>
                    <td className="mono">
                      {pos.target_profit ? `₹${pos.target_profit.toFixed(2)}` : '—'}
                    </td>
                    <td style={{ maxWidth: 160 }}>
                      <span className="truncate">{pos.notes || '—'}</span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button
                          className="btn btn-sm btn-success"
                          onClick={() => closeMutation.mutate(pos.id)}
                        >
                          Close
                        </button>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => deleteMutation.mutate(pos.id)}
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Closed Positions */}
      {closedPositions.length > 0 && (
        <div style={{ marginTop: 'var(--space-xl)' }}>
          <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 600, marginBottom: 'var(--space-sm)', color: 'var(--text-secondary)' }}>
            Closed Positions ({closedPositions.length})
          </h3>
          <div className="table-wrapper" style={{ opacity: 0.7 }}>
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Type</th>
                  <th>Direction</th>
                  <th>Qty</th>
                  <th>Entry</th>
                  <th>Break-Even</th>
                  <th>Closed</th>
                </tr>
              </thead>
              <tbody>
                {closedPositions.map((pos) => (
                  <tr key={pos.id}>
                    <td className="mono" style={{ fontWeight: 600 }}>{pos.ticker}</td>
                    <td>
                      <span className={`badge badge-${pos.trade_type === 'intraday' ? 'green' : pos.trade_type === 'short_selling' ? 'red' : 'blue'}`}>
                        {pos.trade_type.replace('_', ' ')}
                      </span>
                    </td>
                    <td className={pos.direction === 'BUY' ? 'price-up' : 'price-down'}>{pos.direction}</td>
                    <td className="mono">{pos.quantity}</td>
                    <td className="mono">₹{pos.entry_price.toFixed(2)}</td>
                    <td className="mono">₹{pos.exit_price?.toFixed(2) || '—'}</td>
                    <td style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                      {pos.closed_at ? new Date(pos.closed_at).toLocaleString('en-IN') : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Add Position Modal */}
      {showAdd && <AddPositionModal onClose={() => setShowAdd(false)} />}

      {/* Calculator Modal */}
      {showCalc && <CalculatorModal onClose={() => setShowCalc(false)} />}
    </div>
  );
}


/* ── Add Position Modal ──────────────────────────────────────────────── */
function AddPositionModal({ onClose }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    ticker: '',
    trade_type: 'intraday',
    direction: 'BUY',
    quantity: '',
    entry_price: '',
    target_profit: '',
    notes: '',
  });
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: (data) => positionsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      onClose();
    },
    onError: (err) => setError(err.response?.data?.detail || 'Failed to add position'),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.ticker || !form.quantity || !form.entry_price) {
      setError('Ticker, quantity, and entry price are required');
      return;
    }
    mutation.mutate({
      ...form,
      quantity: parseInt(form.quantity),
      entry_price: parseFloat(form.entry_price),
      target_profit: form.target_profit ? parseFloat(form.target_profit) : null,
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Add Position</h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose}><X size={18} /></button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="form-field">
              <label className="label">Ticker *</label>
              <input className="input" placeholder="RELIANCE" value={form.ticker}
                onChange={(e) => setForm({ ...form, ticker: e.target.value.toUpperCase() })} autoFocus />
            </div>
            <div className="form-field">
              <label className="label">Trade Type</label>
              <select className="select" value={form.trade_type}
                onChange={(e) => setForm({ ...form, trade_type: e.target.value })}>
                <option value="intraday">Intraday</option>
                <option value="short_selling">Short Selling</option>
                <option value="long_term">Long-Term</option>
              </select>
            </div>
            <div className="form-field">
              <label className="label">Direction</label>
              <select className="select" value={form.direction}
                onChange={(e) => setForm({ ...form, direction: e.target.value })}>
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
              </select>
            </div>
            <div className="form-field">
              <label className="label">Quantity *</label>
              <input className="input" type="number" min="1" placeholder="100"
                value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} />
            </div>
            <div className="form-field">
              <label className="label">Entry Price (₹) *</label>
              <input className="input" type="number" step="0.01" min="0.01" placeholder="2500.00"
                value={form.entry_price} onChange={(e) => setForm({ ...form, entry_price: e.target.value })} />
            </div>
            <div className="form-field">
              <label className="label">Target Profit (₹)</label>
              <input className="input" type="number" step="0.01" min="0" placeholder="500"
                value={form.target_profit} onChange={(e) => setForm({ ...form, target_profit: e.target.value })} />
            </div>
          </div>

          <div className="form-field" style={{ marginTop: 'var(--space-md)' }}>
            <label className="label">Notes</label>
            <input className="input" placeholder="Optional notes..." value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>

          {error && (
            <div className="form-error">{error}</div>
          )}

          <div className="modal-actions">
            <button type="button" className="btn" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              <Plus size={14} />{mutation.isPending ? 'Saving...' : 'Add Position'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


/* ── Calculator Modal ────────────────────────────────────────────────── */
function CalculatorModal({ onClose }) {
  const [form, setForm] = useState({
    trade_type: 'intraday',
    direction: 'BUY',
    quantity: '',
    entry_price: '',
    target_profit: '',
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: (data) => positionsApi.calculate(data),
    onSuccess: (res) => setResult(res.data),
    onError: (err) => setError(err.response?.data?.detail || 'Calculation error'),
  });

  const handleCalc = (e) => {
    e.preventDefault();
    if (!form.quantity || !form.entry_price) {
      setError('Quantity and entry price are required');
      return;
    }
    setError('');
    mutation.mutate({
      ...form,
      quantity: parseInt(form.quantity),
      entry_price: parseFloat(form.entry_price),
      target_profit: form.target_profit ? parseFloat(form.target_profit) : null,
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 560 }}>
        <div className="modal-header">
          <h2 className="modal-title">Break-Even Calculator</h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose}><X size={18} /></button>
        </div>

        <form onSubmit={handleCalc}>
          <div className="form-grid">
            <div className="form-field">
              <label className="label">Trade Type</label>
              <select className="select" value={form.trade_type}
                onChange={(e) => setForm({ ...form, trade_type: e.target.value })}>
                <option value="intraday">Intraday</option>
                <option value="short_selling">Short Selling</option>
                <option value="long_term">Long-Term (CNC)</option>
              </select>
            </div>
            <div className="form-field">
              <label className="label">Direction</label>
              <select className="select" value={form.direction}
                onChange={(e) => setForm({ ...form, direction: e.target.value })}>
                <option value="BUY">BUY</option>
                <option value="SELL">SELL (Short)</option>
              </select>
            </div>
            <div className="form-field">
              <label className="label">Quantity *</label>
              <input className="input" type="number" min="1" placeholder="100"
                value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} />
            </div>
            <div className="form-field">
              <label className="label">Entry Price (₹) *</label>
              <input className="input" type="number" step="0.01" placeholder="2500.00"
                value={form.entry_price} onChange={(e) => setForm({ ...form, entry_price: e.target.value })} />
            </div>
            <div className="form-field" style={{ gridColumn: 'span 2' }}>
              <label className="label">Target Profit (₹, optional)</label>
              <input className="input" type="number" step="0.01" placeholder="500"
                value={form.target_profit} onChange={(e) => setForm({ ...form, target_profit: e.target.value })} />
            </div>
          </div>

          {error && <div className="form-error">{error}</div>}

          <div className="modal-actions">
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              <Calculator size={14} />{mutation.isPending ? 'Calculating...' : 'Calculate'}
            </button>
          </div>
        </form>

        {/* Results */}
        {result && (
          <div className="calc-results">
            <div className="calc-result-row calc-result-highlight">
              <span>Break-Even Exit Price</span>
              <span className="mono" style={{ fontSize: 'var(--text-lg)', fontWeight: 700 }}>
                ₹{result.breakeven_price?.toFixed(2)}
              </span>
            </div>
            {result.target_price && (
              <div className="calc-result-row calc-result-highlight" style={{ borderColor: 'rgba(0,230,118,0.3)', background: 'var(--green-dim)' }}>
                <span>Target Exit Price</span>
                <span className="mono price-up" style={{ fontSize: 'var(--text-lg)', fontWeight: 700 }}>
                  ₹{result.target_price?.toFixed(2)}
                </span>
              </div>
            )}

            <h4 style={{ marginTop: 'var(--space-md)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Charges Breakdown (Buy Side)
            </h4>
            <div className="calc-charges-grid">
              {Object.entries(result.charges_breakdown_buy || {}).filter(([k]) => k !== 'total').map(([k, v]) => (
                <div key={k} className="calc-charge-item">
                  <span>{k.replace('_', ' ')}</span>
                  <span className="mono">₹{v.toFixed(2)}</span>
                </div>
              ))}
              <div className="calc-charge-item calc-charge-total">
                <span>Total Buy Charges</span>
                <span className="mono">₹{result.total_charges_buy?.toFixed(2)}</span>
              </div>
            </div>

            <h4 style={{ marginTop: 'var(--space-sm)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Charges Breakdown (Sell Side)
            </h4>
            <div className="calc-charges-grid">
              {Object.entries(result.charges_breakdown_sell || {}).filter(([k]) => k !== 'total').map(([k, v]) => (
                <div key={k} className="calc-charge-item">
                  <span>{k.replace('_', ' ')}</span>
                  <span className="mono">₹{v.toFixed(2)}</span>
                </div>
              ))}
              <div className="calc-charge-item calc-charge-total">
                <span>Total Sell Charges</span>
                <span className="mono">₹{result.total_charges_sell?.toFixed(2)}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
