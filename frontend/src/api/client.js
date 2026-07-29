/**
 * API client for TradingHelper backend.
 *
 * Automatically injects the JWT Bearer token from localStorage into
 * every request. On 401 responses, clears the stored token and
 * reloads to the login page.
 */
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor: attach JWT ─────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('th_access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor: handle 401 ────────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid — clear storage and redirect to login
      localStorage.removeItem('th_access_token');
      localStorage.removeItem('th_user');
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  /** Exchange a Google ID token for our own JWT */
  loginWithGoogle: (credential) =>
    api.post('/auth/google', { credential }),
  /** Validate JWT and return current user profile */
  getMe: () => api.get('/auth/me'),
  /** Stateless logout (frontend-side cleanup) */
  logout: () => api.post('/auth/logout'),
};

// ── Watchlist ────────────────────────────────────────────────────────
export const watchlistApi = {
  listAll: () => api.get('/watchlist/'),
  listByMode: (mode) => api.get(`/watchlist/${mode}`),
  add: (data) => api.post('/watchlist/', data),
  update: (id, data) => api.put(`/watchlist/${id}`, data),
  remove: (id) => api.delete(`/watchlist/${id}`),
};

// ── Market Data ──────────────────────────────────────────────────────
export const marketApi = {
  getChart: (ticker, interval = '5m', period = '5d', mode = 'intraday') =>
    api.get(`/market/chart/${ticker}`, { params: { interval, period, mode } }),
  getIndicators: (ticker, mode = 'intraday') =>
    api.get(`/market/indicators/${ticker}`, { params: { mode } }),
  search: (query) => api.get('/market/search', { params: { q: query } }),
  getPrice: (ticker) => api.get(`/market/price/${ticker}`),
};

// ── Positions ────────────────────────────────────────────────────────
export const positionsApi = {
  list: (status) => api.get('/positions/', { params: status ? { status } : {} }),
  create: (data) => api.post('/positions/', data),
  update: (id, data) => api.put(`/positions/${id}`, data),
  remove: (id) => api.delete(`/positions/${id}`),
  calculate: (data) => api.post('/positions/calculate', data),
};

// ── Alerts ───────────────────────────────────────────────────────────
export const alertsApi = {
  list: (params = {}) => api.get('/alerts/', { params }),
  count: () => api.get('/alerts/count'),
  getSettings: () => api.get('/alerts/settings'),
  updateSettings: (data) => api.put('/alerts/settings', data),
  testTelegram: (data) => api.post('/alerts/test-telegram', data),
  testNtfy: (topic) => api.post('/alerts/test-ntfy', { topic }),
};

// ── Health ───────────────────────────────────────────────────────────
export const healthApi = {
  check: () => api.get('/health'),
};

// ── Paper Trades ─────────────────────────────────────────────────────
export const paperTradeApi = {
  /** Fetch live indicator snapshot for a ticker before opening a trade. */
  snapshot: (ticker, mode = 'intraday') =>
    api.get(`/paper-trade/snapshot/${ticker}`, { params: { mode } }),

  /** Open a new paper trade with the (possibly overridden) snapshot data. */
  open: (data) => api.post('/paper-trade/open', data),

  /** Close an open paper trade at the given exit price. */
  close: (id, exitPrice) =>
    api.post(`/paper-trade/close/${id}`, { exit_price: exitPrice }),

  /** Save or update reflection notes on a trade. */
  updateNotes: (id, notes) =>
    api.put(`/paper-trade/${id}/notes`, { reflection_notes: notes }),

  /** List trades, optionally filtered by status ("OPEN" | "CLOSED") or ticker. */
  list: (params = {}) => api.get('/paper-trade/', { params }),
};

export default api;
