/**
 * History Page — trade history + stats cards.
 */
import { useState, useEffect } from 'react'
import { historyApi } from '../../api/client'
import { TrendingUp, TrendingDown, Award, Target, BarChart3 } from 'lucide-react'

export default function HistoryPage() {
  const [stats, setStats] = useState(null)
  const [closedStrategies, setClosedStrategies] = useState([])
  const [dailyStats, setDailyStats] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [s, cs, ds] = await Promise.all([
        historyApi.stats(),
        historyApi.closedStrategies(),
        historyApi.dailyStats(),
      ])
      setStats(s)
      setClosedStrategies(cs.strategies || [])
      setDailyStats(ds.daily_stats || [])
    } catch (err) {
      console.error(err)
    }
    setLoading(false)
  }

  if (loading) return <div className="page-loading"><div className="spinner" /></div>

  return (
    <div className="page">
      <div className="page-header">
        <h2>Reports</h2>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="stats-grid">
          <div className="stat-card featured">
            <BarChart3 size={20} />
            <span className="stat-label">Total P&L</span>
            <span className={`stat-value large ${stats.total_pnl >= 0 ? 'positive' : 'negative'}`}>
              ₹{stats.total_pnl?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
          </div>
          <div className="stat-card">
            <Target size={18} />
            <span className="stat-label">Win Rate</span>
            <span className="stat-value">{stats.win_rate}%</span>
          </div>
          <div className="stat-card">
            <TrendingUp size={18} />
            <span className="stat-label">Best Trade</span>
            <span className="stat-value positive">₹{stats.best_trade?.toLocaleString('en-IN')}</span>
          </div>
          <div className="stat-card">
            <TrendingDown size={18} />
            <span className="stat-label">Worst Trade</span>
            <span className="stat-value negative">₹{stats.worst_trade?.toLocaleString('en-IN')}</span>
          </div>
          <div className="stat-card">
            <Award size={18} />
            <span className="stat-label">Winning</span>
            <span className="stat-value">{stats.winning_trades}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Losing</span>
            <span className="stat-value">{stats.losing_trades}</span>
          </div>
        </div>
      )}

      {/* Closed Strategies */}
      <div className="section">
        <h3>Closed Strategies</h3>
        {closedStrategies.length === 0 ? (
          <div className="empty-state">
            <p>No closed strategies yet</p>
          </div>
        ) : (
          <div className="strategy-cards">
            {closedStrategies.map((s) => (
              <div key={s._id} className="strategy-card closed">
                <div className="strategy-card-header">
                  <h4>{s.name}</h4>
                  <span className="badge badge-closed">Closed</span>
                </div>
                <div className="strategy-card-body">
                  <span>{s.underlying}</span>
                  <span>{s.total_legs} legs</span>
                  <span>{s.exit_reasons?.join(', ')}</span>
                </div>
                <div className={`strategy-pnl ${(s.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                  ₹{(s.total_pnl || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
                <div className="strategy-dates">
                  <span>Created: {new Date(s.created_at).toLocaleDateString('en-IN')}</span>
                  {s.closed_at && <span>Closed: {new Date(s.closed_at).toLocaleDateString('en-IN')}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Daily PnL Table */}
      <div className="section">
        <h3>Daily Profit & Loss</h3>
        <div className="oc-container" style={{ marginTop: '16px' }}>
          <table className="oc-table">
            <thead>
              <tr>
                <th className="left">Date</th>
                <th className="center">Trades</th>
                <th className="right">Net P&L</th>
              </tr>
            </thead>
            <tbody>
              {dailyStats.length === 0 ? (
                <tr><td colSpan="3" className="center text-muted">No daily stats available</td></tr>
              ) : (
                dailyStats.map((d, idx) => (
                  <tr key={idx}>
                    <td className="left">{new Date(d.date).toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' })}</td>
                    <td className="center">{d.trades}</td>
                    <td className={`right ${d.pnl >= 0 ? 'positive font-bold' : 'negative font-bold'}`}>
                      ₹{d.pnl.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
