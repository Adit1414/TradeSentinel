/**
 * AuthContext — provides user session state and Google sign-in/out helpers
 * to the entire React tree.
 *
 * Storage strategy:
 *   - JWT stored in localStorage under key "th_access_token"
 *   - User profile cached under key "th_user" (JSON)
 *   - On mount, the token is re-validated against GET /api/auth/me
 *     to ensure it is still valid (not expired, user still exists).
 */

import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { authApi } from '../api/client';

const AuthContext = createContext(null);

const TOKEN_KEY = 'th_access_token';
const USER_KEY = 'th_user';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const cached = localStorage.getItem(USER_KEY);
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [loading, setLoading] = useState(true); // true until session is verified

  // ── On mount: validate stored token ────────────────────────────────────────
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    if (!storedToken) {
      setLoading(false);
      return;
    }

    authApi
      .getMe()
      .then((res) => {
        setUser(res.data);
        localStorage.setItem(USER_KEY, JSON.stringify(res.data));
      })
      .catch(() => {
        // Token is invalid or expired — clear everything
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setUser(null);
        setToken(null);
      })
      .finally(() => setLoading(false));
  }, []);

  // ── Login with Google credential ────────────────────────────────────────────
  const login = useCallback(async (googleCredential) => {
    const res = await authApi.loginWithGoogle(googleCredential);
    const { access_token, user: userData } = res.data;

    localStorage.setItem(TOKEN_KEY, access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(userData));
    setToken(access_token);
    setUser(userData);

    return userData;
  }, []);

  // ── Logout ──────────────────────────────────────────────────────────────────
  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Stateless — ignore errors
    }

    // Revoke Google session if GSI is loaded
    if (window.google?.accounts?.id) {
      window.google.accounts.id.disableAutoSelect();
    }

    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

/** Hook to access auth context from any component. */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
