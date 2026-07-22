import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'

// Pages
import LoginPage from './pages/LoginPage'
import HomePage from './pages/user/HomePage'
import StrategyList from './pages/user/StrategyList'
import StrategyBuilder from './pages/user/StrategyBuilder'
import StrategyDetail from './pages/user/StrategyDetail'
import WalletPage from './pages/user/WalletPage'
import HistoryPage from './pages/user/HistoryPage'
import ProfilePage from './pages/user/ProfilePage'
import TradeHistoryPage from './pages/user/TradeHistoryPage'
import MarketsPage from './pages/user/MarketsPage'

import AdminDashboard from './pages/admin/AdminDashboard'
import AdminUsers from './pages/admin/AdminUsers'
import AdminGlobal from './pages/admin/AdminGlobal'

import Backtester from './pages/user/Backtester'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public Route */}
        <Route path="/login" element={<LoginPage />} />

        {/* Redirect root based on auth */}
        <Route path="/" element={<Navigate to="/home" replace />} />

        {/* User Routes (with BottomNav) */}
        <Route element={<ProtectedRoute requiredRole="user"><Layout /></ProtectedRoute>}>
          <Route path="/home" element={<HomePage />} />
          <Route path="/strategies" element={<StrategyList />} />
          <Route path="/wallet" element={<WalletPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/markets" element={<MarketsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>

        {/* User Routes (No BottomNav) */}
        <Route element={<ProtectedRoute requiredRole="user" />}>
          <Route path="/strategies/new" element={<StrategyBuilder />} />
          <Route path="/strategies/:id" element={<StrategyDetail />} />
          <Route path="/trade-history" element={<TradeHistoryPage />} />
          <Route path="/backtester" element={<Backtester />} />
        </Route>

        {/* Admin Routes (with BottomNav) */}
        <Route element={<ProtectedRoute requiredRole="admin"><Layout /></ProtectedRoute>}>
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/users" element={<AdminUsers />} />
          <Route path="/admin/global" element={<AdminGlobal />} />
          <Route path="/admin/profile" element={<ProfilePage />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
