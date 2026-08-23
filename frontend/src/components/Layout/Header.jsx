import { useState, useRef, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { LogOut, RefreshCw, ChevronDown, Menu } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import './Layout.css';

const pageTitles = {
  '/': 'Dashboard',
  '/positions': 'Position Tracker',
  '/alerts': 'Alert History',
  '/journal': 'Paper Trade Journal',
};

export default function Header({ toggleSidebar }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  const title =
    pageTitles[location.pathname] ||
    (location.pathname.startsWith('/chart/')
      ? `Chart — ${location.pathname.split('/chart/')[1]?.toUpperCase()}`
      : 'TradingHelper');

  // Close menu on outside click
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  async function handleLogout() {
    setMenuOpen(false);
    await logout();
    navigate('/login', { replace: true });
  }

  // Get initials from name (fallback if avatar fails to load)
  const initials = user?.name
    ? user.name
        .split(' ')
        .slice(0, 2)
        .map((n) => n[0])
        .join('')
        .toUpperCase()
    : '?';

  return (
    <header className="header">
      <div className="header-left">
        <button className="btn btn-ghost btn-icon mobile-menu-btn" onClick={toggleSidebar} title="Open Menu">
          <Menu size={20} />
        </button>
        <h1 className="header-title">{title}</h1>
      </div>
      <div className="header-actions">
        <button className="btn btn-ghost btn-icon" title="Refresh data">
          <RefreshCw size={16} />
        </button>

        {/* User avatar + dropdown */}
        {user && (
          <div className="header-user-menu" ref={menuRef}>
            <button
              className="header-user-btn"
              onClick={() => setMenuOpen((o) => !o)}
              title={user.name}
            >
              {user.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.name}
                  className="header-avatar-img"
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />
              ) : null}
              <span className="header-avatar-initials">{initials}</span>
              <span className="header-user-name">{user.name.split(' ')[0]}</span>
              <ChevronDown size={14} className={`header-chevron ${menuOpen ? 'open' : ''}`} />
            </button>

            {menuOpen && (
              <div className="header-dropdown">
                <div className="header-dropdown-info">
                  <span className="header-dropdown-name">{user.name}</span>
                  <span className="header-dropdown-email">{user.email}</span>
                </div>
                <div className="header-dropdown-divider" />
                <button className="header-dropdown-item header-dropdown-logout" onClick={handleLogout}>
                  <LogOut size={14} />
                  Sign out
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
