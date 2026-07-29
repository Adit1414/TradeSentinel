/**
 * ProtectedRoute — wraps routes that require authentication.
 * Redirects to /login if the user is not logged in.
 * Shows a full-screen spinner while the auth session is being validated.
 */

import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="auth-loading-screen">
        <div className="auth-loading-spinner" />
        <span className="auth-loading-text">Verifying session…</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
