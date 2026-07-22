/**
 * User Home Page — dashboard with wallet card, active strategies overview, quick actions.
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { walletApi, strategyApi, historyApi } from '../../api/client'
import { Plus, TrendingUp, TrendingDown, ArrowRight, Wallet, BarChart3, Globe } from 'lucide-react'

export default function HomePage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [wallet, setWallet] = useState(null)
  const [activeStrategies, setActiveStrategies] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 1000) // Refresh every 1s
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [w, s, st] = await Promise.all([
        walletApi.get(),
        strategyApi.list('active'),
        historyApi.stats(),
      ])
      setWallet(w)
      setActiveStrategies(s.strategies || [])
      setStats(st)
    } catch (err) {
      console.error('Home data load error:', err)
    }
    setLoading(false)
  }

  if (loading) {
    return <div className="page-loading"><div className="spinner" /></div>
  }

  return (
    <div className="page home-page">
      <div className="page-header">
        <h2>Welcome, {user?.name?.split(' ')[0]} 👋</h2>
        <p className="page-subtitle">Paper Trading Dashboard</p>
      </div>

      {/* Wallet Card */}
      <div className="wallet-card-hero">
        <div className="wallet-card-bg" />
        <div className="wallet-card-content">
          <span className="wallet-label">Virtual Chips Balance</span>
          <h1 className="wallet-amount">
            ₹{(wallet?.virtual_chips_balance || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </h1>
          <div className="wallet-meta" style={{ marginBottom: '12px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '12px' }}>
            <span style={{ color: 'rgba(255,255,255,0.8)' }}>Available Margin: <strong style={{ color: '#fff' }}>₹{(wallet?.available_margin ?? wallet?.virtual_chips_balance ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong></span>
            <span style={{ color: 'rgba(255,255,255,0.8)' }}>Margin Used: <strong style={{ color: '#fff' }}>₹{(wallet?.used_margin || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong></span>
          </div>
          <div className="wallet-meta">
            <div className={`wallet-pnl ${(wallet?.unrealized_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
              {(wallet?.unrealized_pnl || 0) >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              <span>₹{Math.abs(wallet?.unrealized_pnl || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })} unrealized</span>
            </div>
            <span className="wallet-net">Net: ₹{(wallet?.net_worth || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions">
        <button className="action-card primary" onClick={() => navigate('/strategies/new')}>
          <Plus size={24} />
          <span>New Strategy</span>
        </button>
        <button className="action-card" onClick={() => navigate('/history')}>
          <BarChart3 size={24} />
          <span>Reports</span>
        </button>
        <button className="action-card" onClick={() => navigate('/wallet')}>
          <Wallet size={24} />
          <span>Wallet</span>
        </button>
        <button className="action-card" onClick={() => window.open('/backtester', '_blank')} style={{ background: 'var(--primary-hover)', color: 'white' }}>
          <Globe size={24} />
          <span>Subh Muhurt</span>
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-label">Total P&L</span>
            <span className={`stat-value ${stats.total_pnl >= 0 ? 'positive' : 'negative'}`}>
              ₹{stats.total_pnl?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Win Rate</span>
            <span className="stat-value">{stats.win_rate}%</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Total Trades</span>
            <span className="stat-value">{stats.total_trades}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Active</span>
            <span className="stat-value">{stats.active_strategies}</span>
          </div>
        </div>
      )}

      {/* Active Strategies */}
      <div className="section">
        <div className="section-header">
          <h3>Active Strategies</h3>
          <button className="text-btn" onClick={() => navigate('/strategies')}>
            View All <ArrowRight size={14} />
          </button>
        </div>

        {activeStrategies.length === 0 ? (
          <div className="empty-state">
            <p>No active strategies</p>
            <button className="btn-primary" onClick={() => navigate('/strategies/new')}>
              Create Your First Strategy
            </button>
          </div>
        ) : (
          <div className="strategy-cards">
            {activeStrategies.slice(0, 3).map((s) => (
              <div
                key={s._id}
                className="strategy-card"
                onClick={() => navigate(`/strategies/${s._id}`)}
              >
                <div className="strategy-card-header">
                  <h4>{s.name}</h4>
                  <span className="badge badge-active">Active</span>
                </div>
                <div className="strategy-card-body">
                  <span className="strategy-underlying">{s.underlying}</span>
                  <span className="strategy-legs">{s.open_legs}/{s.total_legs} legs open</span>
                </div>
                <div className={`strategy-pnl ${(s.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                  ₹{(s.total_pnl || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
