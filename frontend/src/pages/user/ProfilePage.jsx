/**
 * Profile Page — Compact & Premium Dashboard
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { historyApi } from '../../api/client'
import {
  User, LogOut, Shield, History, Wallet, TrendingUp, TrendingDown,
  Award, ChevronRight, Settings, Sun, Moon
} from 'lucide-react'

export default function ProfilePage() {
  const { user, logout, isAdmin } = useAuth()
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark')

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
    document.documentElement.setAttribute('data-theme', newTheme)
    localStorage.setItem('theme', newTheme)
  }

  useEffect(() => {
    historyApi.stats().then(setStats).catch(() => null)
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="page profile-page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Profile</h2>
        <button 
          onClick={toggleTheme} 
          style={{ 
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            width: '36px', height: '36px', 
            borderRadius: '50%', 
            background: 'var(--bg-hover)', 
            border: '1px solid var(--border)',
            color: 'var(--text)',
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
          }}
          title="Toggle Theme"
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>

      {/* User Avatar Card */}
      <div className="profile-card">
        <div className="profile-avatar">
          <User size={44} />
        </div>
        <h3>{user?.name}</h3>
        <p className="profile-email">{user?.email}</p>
        
        {isAdmin && (
          <div className="admin-badge">
            <Shield size={16} /> Admin
          </div>
        )}
      </div>

      {/* Performance Summary Cards */}
      {stats && (
        <div className="profile-stats-grid">
          <div className="profile-stat-card">
            <span className="stat-label">Total Realized P&L</span>
            <div className={`stat-value-large ${(stats.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
              {(stats.total_pnl || 0) >= 0 ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
              {(stats.total_pnl || 0) >= 0 ? '+' : '-'}₹{Math.abs(stats.total_pnl || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <span className="stat-sub">{stats.total_trades || 0} Total Executions</span>
          </div>

          <div className="profile-stat-card">
            <span className="stat-label">Win Rate</span>
            <div className="stat-value-large positive">
              <Award size={20} />
              {stats.win_rate || 0}%
            </div>
            <span className="stat-sub">{stats.winning_trades || 0} Wins / {stats.losing_trades || 0} Losses</span>
          </div>
        </div>
      )}

      {/* Premium Quick Navigation Menu */}
      <div className="section">
        <div className="profile-menu-list">
          <div className="profile-menu-item" onClick={() => navigate('/trade-history')}>
            <div className="menu-item-left">
              <div className="menu-icon-box primary">
                <History size={20} />
              </div>
              <div className="menu-item-text">
                <strong>Trading History & Reports</strong>
                <p>View closed trades, daily P&L, and executions</p>
              </div>
            </div>
            <ChevronRight size={18} className="text-muted" />
          </div>

          <div className="profile-menu-item" onClick={() => navigate('/wallet')}>
            <div className="menu-item-left">
              <div className="menu-icon-box success">
                <Wallet size={20} />
              </div>
              <div className="menu-item-text">
                <strong>Virtual Wallet & Chips</strong>
                <p>Manage balance, add funds & transaction logs</p>
              </div>
            </div>
            <ChevronRight size={18} className="text-muted" />
          </div>
          <div className="profile-menu-item" onClick={() => navigate('/broker-integration')}>
            <div className="menu-item-left">
              <div className="menu-icon-box" style={{ background: 'rgba(255,165,0,0.1)', color: 'orange' }}>
                <Settings size={20} />
              </div>
              <div className="menu-item-text">
                <strong>Broker Integration</strong>
                <p>Connect Upstox for live market data</p>
              </div>
            </div>
            <ChevronRight size={18} className="text-muted" />
          </div>
        </div>
      </div>

      {/* Account Info Section */}
      <div className="section">
        <div className="profile-info-list">
          <div className="profile-info-item">
            <span>Role</span>
            <strong>{user?.role?.toUpperCase()}</strong>
          </div>
          <div className="profile-info-item">
            <span>Status</span>
            <strong className={`status-${user?.status}`}>{user?.status?.toUpperCase()}</strong>
          </div>
          <div className="profile-info-item">
            <span>Joined</span>
            <strong>{new Date(user?.created_at).toLocaleDateString('en-IN')}</strong>
          </div>
        </div>
      </div>

      {/* Logout Action */}
      <div className="profile-actions">
        <button className="btn-danger btn-full" onClick={handleLogout}>
          <LogOut size={18} /> Sign Out
        </button>
      </div>
    </div>
  )
}
