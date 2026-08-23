/**
 * LoginPage — Google Sign-In landing page.
 *
 * Uses the Google Identity Services (GSI) One-Tap / button SDK.
 * The Google client-id is injected from the meta tag set in index.html.
 *
 * Flow:
 *   1. Page renders with animated hero + glassmorphism card
 *   2. GSI SDK is already loaded (script tag in index.html)
 *   3. On mount, we call google.accounts.id.initialize + renderButton
 *   4. User clicks the Google button → credential callback fires
 *   5. We POST the ID token to our backend → get a JWT back
 *   6. AuthContext stores the JWT and user profile
 *   7. Navigate to the dashboard
 */

import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './LoginPage.css';

// The GOOGLE_CLIENT_ID is embedded in the page via a <meta> tag in index.html
function getGoogleClientId() {
  const meta = document.querySelector('meta[name="google-signin-client_id"]');
  return meta?.content || '';
}

export default function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const buttonRef = useRef(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // If already logged in, skip the login page
  useEffect(() => {
    if (user) navigate('/', { replace: true });
  }, [user, navigate]);

  // Initialize Google One-Tap + render button
  useEffect(() => {
    const clientId = getGoogleClientId();
    if (!clientId || clientId.startsWith('REPLACE')) {
      setError(
        'Google Client ID not configured. Edit GOOGLE_CLIENT_ID in backend/.env and index.html.'
      );
      return;
    }

    const initGoogle = () => {
      if (!window.google?.accounts?.id) return;

      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleCredentialResponse,
        auto_select: false,
        cancel_on_tap_outside: true,
      });

      if (buttonRef.current) {
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: 'filled_black',
          size: 'large',
          shape: 'pill',
          text: 'signin_with',
          logo_alignment: 'left',
          width: 280,
        });
      }

      // Also show the One-Tap prompt
      window.google.accounts.id.prompt();
    };

    // GSI might not be loaded yet if this page renders before the async script
    if (window.google?.accounts?.id) {
      initGoogle();
    } else {
      window.addEventListener('load', initGoogle);
      return () => window.removeEventListener('load', initGoogle);
    }
  }, []);

  async function handleCredentialResponse(response) {
    setError('');
    setLoading(true);
    try {
      await login(response.credential);
      navigate('/', { replace: true });
    } catch (err) {
      console.error('Login error:', err);
      const detail = err?.response?.data?.detail;
      const msg =
        (typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : null) ||
        err?.message ||
        'Login failed. Please try again or check your network.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      {/* Animated background orbs */}
      <div className="login-bg">
        <div className="login-orb login-orb-1" />
        <div className="login-orb login-orb-2" />
        <div className="login-orb login-orb-3" />
        <div className="login-grid" />
      </div>

      {/* Main card */}
      <div className="login-card">
        {/* Logo / Brand */}
        <div className="login-brand">
          <div className="login-logo">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path
                d="M6 30L14 18L20 24L28 12L34 20"
                stroke="url(#grad1)"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="34" cy="20" r="3" fill="#00e676" />
              <defs>
                <linearGradient id="grad1" x1="6" y1="30" x2="34" y2="12" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#2979ff" />
                  <stop offset="1" stopColor="#00e676" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <h1 className="login-title">TradeSentinel</h1>
          <p className="login-subtitle">NSE Stock Intelligence Dashboard</p>
        </div>

        {/* Feature pills */}
        <div className="login-features">
          <span className="login-feature-pill">📊 4-Indicator Confluence</span>
          <span className="login-feature-pill">⚡ Real-time Alerts</span>
          <span className="login-feature-pill">📓 Paper Trade Journal</span>
        </div>

        {/* Divider */}
        <div className="login-divider">
          <span>Sign in to continue</span>
        </div>

        {/* Google button container */}
        <div className="login-google-btn-wrap">
          {loading ? (
            <div className="login-spinner-wrap">
              <div className="login-spinner" />
              <span>Authenticating…</span>
            </div>
          ) : (
            <div ref={buttonRef} className="login-google-btn" />
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="login-error">
            <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            {error}
          </div>
        )}

        <p className="login-disclaimer">
          For personal educational use only. Not financial advice.
        </p>
      </div>
    </div>
  );
}
