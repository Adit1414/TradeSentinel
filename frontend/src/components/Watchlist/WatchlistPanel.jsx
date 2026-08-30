import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, BarChart3, TrendingUp, TrendingDown, Clock, Eye, EyeOff, BookOpen } from 'lucide-react';
import { watchlistApi } from '../../api/client';
import AddTickerModal from './AddTickerModal';
import PaperTradeModal from '../PaperTrade/PaperTradeModal';
import './Watchlist.css';

const MODE_CONFIG = {
  intraday: {
    label: 'Intraday',
    sublabel: 'Buy Side · 5min',
    icon: TrendingUp,
    color: 'green',
    badgeClass: 'badge-green',
  },
  long_term: {
    label: 'Long-Term',
    sublabel: 'Delivery · Daily',
    icon: Clock,
    color: 'blue',
    badgeClass: 'badge-blue',
  },
};

export default function WatchlistPanel({ mode }) {
  const [showAdd, setShowAdd] = useState(false);
  const [paperTradeTicker, setPaperTradeTicker] = useState(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const config = MODE_CONFIG[mode];

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['watchlist', mode],
    queryFn: () => watchlistApi.listByMode(mode).then((r) => r.data),
    refetchInterval: 60000,
  });

  const removeMutation = useMutation({
    mutationFn: (id) => watchlistApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist', mode] }),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }) => watchlistApi.update(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist', mode] }),
  });

  const Icon = config.icon;

  return (
    <div className="watchlist-panel glass-card">
      {/* Header */}
      <div className="watchlist-header">
        <div className="watchlist-header-left">
          <div className={`watchlist-mode-icon watchlist-mode-icon-${config.color}`}>
            <Icon size={16} />
          </div>
          <div>
            <h3 className="watchlist-title">{config.label}</h3>
            <span className="watchlist-subtitle">{config.sublabel}</span>
          </div>
        </div>
        <button className="btn btn-sm btn-primary" onClick={() => setShowAdd(true)}>
          <Plus size={14} />
          Add
        </button>
      </div>

      {/* Items */}
      <div className="watchlist-items">
        {isLoading ? (
          <div className="watchlist-loading">
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton" style={{ height: 44, marginBottom: 4 }} />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="empty-state" style={{ padding: '24px 16px' }}>
            <Icon size={28} strokeWidth={1.5} />
            <p style={{ fontSize: 'var(--text-xs)' }}>No stocks added yet</p>
          </div>
        ) : (
          items.map((item, index) => (
            <div
              key={item.id}
              className={`watchlist-item ${!item.is_active ? 'watchlist-item-inactive' : ''}`}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div
                className="watchlist-item-info"
                onClick={() => navigate(`/chart/${item.ticker}?mode=${mode}`)}
                role="button"
                tabIndex={0}
              >
                <span className="watchlist-item-ticker mono">{item.ticker}</span>
                <span className="watchlist-item-name truncate">
                  {item.display_name || item.ticker}
                </span>
              </div>

              <div className="watchlist-item-actions">
                <button
                  className="btn btn-ghost btn-sm btn-icon"
                  title="Log Paper Trade"
                  onClick={(e) => { e.stopPropagation(); setPaperTradeTicker(item.ticker); }}
                >
                  <BookOpen size={14} />
                </button>
                <button
                  className="btn btn-ghost btn-sm btn-icon"
                  onClick={() => navigate(`/chart/${item.ticker}?mode=${mode}`)}
                >
                  <BarChart3 size={14} />
                </button>
                <button
                  className="btn btn-ghost btn-sm btn-icon"
                  title={item.is_active ? 'Pause tracking' : 'Resume tracking'}
                  onClick={() =>
                    toggleMutation.mutate({ id: item.id, is_active: !item.is_active })
                  }
                >
                  {item.is_active ? <Eye size={14} /> : <EyeOff size={14} />}
                </button>
                <button
                  className="btn btn-ghost btn-sm btn-icon"
                  title="Remove"
                  onClick={() => removeMutation.mutate(item.id)}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Count */}
      <div className="watchlist-footer">
        <span className={`badge ${config.badgeClass}`}>
          {items.filter((i) => i.is_active).length} active
        </span>
      </div>

      {/* Add Modal */}
      {showAdd && (
        <AddTickerModal mode={mode} onClose={() => setShowAdd(false)} />
      )}

      {/* Paper Trade Modal */}
      {paperTradeTicker && (
        <PaperTradeModal
          ticker={paperTradeTicker}
          initialMode={mode}
          onClose={() => setPaperTradeTicker(null)}
        />
      )}
    </div>
  );
}
