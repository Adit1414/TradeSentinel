import { useState } from 'react';
import { createPortal } from 'react-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { X, Search, Plus } from 'lucide-react';
import { watchlistApi } from '../../api/client';

const MODE_LABELS = {
  intraday: 'Intraday',
  short_selling: 'Short Selling',
  long_term: 'Long-Term',
};

export default function AddTickerModal({ mode, onClose }) {
  const [ticker, setTicker] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const queryClient = useQueryClient();

  const addMutation = useMutation({
    mutationFn: (data) => watchlistApi.add(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist', mode] });
      onClose();
    },
    onError: (err) => {
      setError(err.response?.data?.detail || 'Failed to add ticker');
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!ticker.trim()) {
      setError('Ticker symbol is required');
      return;
    }
    setError('');
    addMutation.mutate({
      ticker: ticker.trim().toUpperCase(),
      display_name: displayName.trim() || null,
      mode,
    });
  };

  return createPortal(
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">
            Add to {MODE_LABELS[mode]} Watchlist
          </h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 'var(--space-md)' }}>
            <label className="label">NSE Ticker Symbol *</label>
            <input
              className="input"
              type="text"
              placeholder="e.g. RELIANCE, TCS, INFY"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              autoFocus
            />
          </div>

          <div style={{ marginBottom: 'var(--space-md)' }}>
            <label className="label">Display Name (optional)</label>
            <input
              className="input"
              type="text"
              placeholder="e.g. Reliance Industries"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 4 }}>
              Leave empty to auto-detect from market data
            </p>
          </div>

          {error && (
            <div style={{
              padding: 'var(--space-sm) var(--space-md)',
              background: 'var(--red-dim)',
              border: '1px solid rgba(255,23,68,0.3)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--red)',
              fontSize: 'var(--text-sm)',
              marginBottom: 'var(--space-md)',
            }}>
              {error}
            </div>
          )}

          <div className="modal-actions">
            <button type="button" className="btn" onClick={onClose}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={addMutation.isPending}
            >
              <Plus size={14} />
              {addMutation.isPending ? 'Adding...' : 'Add Stock'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
