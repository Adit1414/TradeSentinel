import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  BarChart3,
  Wallet,
  Bell,
  Activity,
  BookOpen,
} from 'lucide-react';
import './Layout.css';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/positions', label: 'Positions', icon: Wallet },
  { path: '/journal', label: 'Journal', icon: BookOpen },
  { path: '/alerts', label: 'Alerts', icon: Bell },
];

export default function Sidebar({ isOpen, closeSidebar }) {
  const location = useLocation();

  return (
    <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Activity size={22} strokeWidth={2.5} />
        </div>
        <div className="sidebar-logo-text">
          <span className="sidebar-logo-title">TradingHelper</span>
          <span className="sidebar-logo-sub">NSE Dashboard</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {navItems.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            onClick={closeSidebar}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`
            }
          >
            <Icon size={18} />
            <span>{label}</span>
          </NavLink>
        ))}

        {location.pathname.startsWith('/chart') && (
          <NavLink to={location.pathname} onClick={closeSidebar} className="sidebar-link sidebar-link-active">
            <BarChart3 size={18} />
            <span>Chart</span>
          </NavLink>
        )}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-market-status">
          <div className="market-dot" />
          <span>Educational Only</span>
        </div>
      </div>
    </aside>
  );
}
