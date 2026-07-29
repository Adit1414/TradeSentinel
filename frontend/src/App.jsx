import { Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import Layout from './components/Layout/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ChartPage from './pages/ChartPage';
import PositionsPage from './pages/PositionsPage';
import AlertsPage from './pages/AlertsPage';
import JournalPage from './pages/JournalPage';

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public route */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected routes — require authentication */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/chart/:ticker" element={<ChartPage />} />
                  <Route path="/positions" element={<PositionsPage />} />
                  <Route path="/alerts" element={<AlertsPage />} />
                  <Route path="/journal" element={<JournalPage />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </AuthProvider>
  );
}
