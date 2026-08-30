import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, Target, Bell, BookOpen, Activity, BarChart3 } from 'lucide-react';
import './Layout.css';
import logoImg from '../../assets/logo.png';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/positions', label: 'Positions', icon: Target },
  { path: '/journal', label: 'Journal', icon: BookOpen },
  { path: '/alerts', label: 'Alerts', icon: Bell },
  { path: '/backtest', label: 'Backtester', icon: Activity },
];

export default function Sidebar({ isOpen, closeSidebar }) {
  const location = useLocation();

  return (
    <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <img src={logoImg} alt="TradeSentinel Logo" className="sidebar-logo-img" />
        </div>
        <div className="sidebar-logo-text">
          <span className="sidebar-logo-title">TradeSentinel</span>
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
