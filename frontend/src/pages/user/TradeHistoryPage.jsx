/**
 * Dedicated Trade History & Reports Page
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { historyApi } from '../../api/client'
import {
  ArrowLeft, History, Calendar, TrendingUp, TrendingDown,
  Award, Activity, ChevronRight
} from 'lucide-react'

const formatISTDateTime = (dateStr) => {
  if (!dateStr) return ''
  let str = String(dateStr).trim()
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(str) && !str.endsWith('Z') && !str.includes('+') && !str.includes('Z')) {
    str += 'Z'
  }
  const date = new Date(str)
  if (isNaN(date.getTime())) return String(dateStr)

  return date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
    timeZone: 'Asia/Kolkata'
  })
}

export default function TradeHistoryPage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [historyTab, setHistoryTab] = useState('closed') // 'closed' | 'daily' | 'trades'
  const [closedStrategies, setClosedStrategies] = useState([])
  const [dailyStats, setDailyStats] = useState([])
  const [trades, setTrades] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    setLoading(true)
    try {
      const [statsRes, closedRes, dailyRes, tradesRes] = await Promise.all([
        historyApi.stats().catch(() => null),
        historyApi.closedStrategies({ limit: 100 }).catch(() => ({ strategies: [] })),
        historyApi.dailyStats().catch(() => ({ daily_stats: [] })),
        historyApi.trades({ limit: 100 }).catch(() => ({ trades: [] }))
      ])

      if (statsRes) setStats(statsRes)
      if (closedRes?.strategies) setClosedStrategies(closedRes.strategies)
      if (dailyRes?.daily_stats) setDailyStats(dailyRes.daily_stats)
      if (tradesRes?.trades) setTrades(tradesRes.trades)
    } catch (err) {
      console.error('Error loading history:', err)
    }
    setLoading(false)
  }

  return (
    <div className="page trade-history-page">
      {/* Header with Back Button */}
      <div className="nav-header-bar">
        <button className="btn-back-icon" onClick={() => navigate('/profile')}>
          <ArrowLeft size={20} />
        </button>
        <h2>Trading History & Reports</h2>
      </div>

      {/* Performance Summary Banner */}
      {stats && (
        <div className="history-summary-grid">
          <div className="history-summary-card">
            <span className="summary-label">Total Realized P&L</span>
            <div className={`summary-value ${(stats.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
              {(stats.total_pnl || 0) >= 0 ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
              {(stats.total_pnl || 0) >= 0 ? '+' : '-'}₹{Math.abs(stats.total_pnl || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
          </div>

          <div className="history-summary-card">
            <span className="summary-label">Win Rate</span>
            <div className="summary-value positive">
              <Award size={20} />
              {stats.win_rate || 0}%
            </div>
            <span className="summary-sub">{stats.winning_trades || 0}W / {stats.losing_trades || 0}L</span>
          </div>
        </div>
      )}

      {/* History Sub-tabs */}
      <div className="history-tab-chips container-padding">
        <button
          className={`chip ${historyTab === 'closed' ? 'active' : ''}`}
          onClick={() => setHistoryTab('closed')}
        >
          Closed Trades ({closedStrategies.length})
        </button>
        <button
          className={`chip ${historyTab === 'daily' ? 'active' : ''}`}
          onClick={() => setHistoryTab('daily')}
        >
          Daily History ({dailyStats.length})
        </button>
        <button
          className={`chip ${historyTab === 'trades' ? 'active' : ''}`}
          onClick={() => setHistoryTab('trades')}
        >
          Executions ({trades.length})
        </button>
      </div>

      {loading ? (
        <div className="page-loading"><div className="spinner" /></div>
      ) : (
        <div className="history-content-container">
          {/* TAB 1: CLOSED STRATEGIES */}
          {historyTab === 'closed' && (
            <div className="history-cards-container">
              {closedStrategies.length === 0 ? (
                <div className="empty-state">
                  <History size={36} className="text-muted" />
                  <p>No closed strategies recorded yet</p>
                </div>
              ) : (
                closedStrategies.map((s) => {
                  const pnl = s.total_pnl || 0
                  const isPos = pnl >= 0
                  return (
                    <div
                      key={s._id}
                      className={`history-item-card ${isPos ? 'positive' : 'negative'}`}
                      onClick={() => navigate(`/strategies/${s._id}`)}
                    >
                      <div className="history-item-header">
                        <div className="history-item-left">
                          <span className="history-underlying-badge">{s.underlying}</span>
                          <h4 className="history-item-name">{s.name}</h4>
                        </div>
                        <div className={`history-pnl-pill ${isPos ? 'positive' : 'negative'}`}>
                          {isPos ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                          <span>{isPos ? '+' : '-'}₹{Math.abs(pnl).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                        </div>
                      </div>

                      <div className="history-item-footer">
                        <div className="history-meta">
                          <span>{s.total_legs} Legs</span>
                          <span className="dot-sep">•</span>
                          <span>{formatISTDateTime(s.closed_at || s.created_at)}</span>
                        </div>

                        {s.exit_reasons && s.exit_reasons.length > 0 && (
                          <div className="history-reason-tags">
                            {s.exit_reasons.map((r, idx) => (
                              <span key={idx} className="exit-reason-tag">
                                {r.replace('_', ' ')}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          )}

          {/* TAB 2: DAILY HISTORY */}
          {historyTab === 'daily' && (
            <div className="daily-stats-container">
              {dailyStats.length === 0 ? (
                <div className="empty-state">
                  <Calendar size={36} className="text-muted" />
                  <p>No daily trading data recorded</p>
                </div>
              ) : (
                dailyStats.map((d, i) => {
                  const isPos = d.pnl >= 0
                  return (
                    <div key={i} className="daily-history-row">
                      <div className="daily-date-info">
                        <Calendar size={16} className="text-muted" />
                        <span className="daily-date-text">
                          {new Date(d.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                        </span>
                        <span className="daily-trade-badge">({d.trades} trade{d.trades > 1 ? 's' : ''})</span>
                      </div>
                      <div className={`daily-pnl-value ${isPos ? 'positive' : 'negative'}`}>
                        {isPos ? <TrendingUp size={15} /> : <TrendingDown size={15} />}
                        <span>{isPos ? '+' : '-'}₹{Math.abs(d.pnl).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          )}

          {/* TAB 3: ITEMIZED EXECUTIONS */}
          {historyTab === 'trades' && (
            <div className="trades-executions-container">
              {trades.length === 0 ? (
                <div className="empty-state">
                  <Activity size={36} className="text-muted" />
                  <p>No trade executions recorded</p>
                </div>
              ) : (
                trades.map((t) => {
                  const isPos = (t.pnl || 0) >= 0
                  return (
                    <div key={t._id} className="trade-execution-row">
                      <div className="trade-exec-left">
                        <span className={`side-badge ${t.side?.toLowerCase()}`}>{t.side}</span>
                        <div className="trade-exec-symbol">
                          <strong>{t.symbol} {t.strike} {t.option_type}</strong>
                          <span className="trade-exec-qty">{t.qty} Qty @ ₹{(t.exit_price || t.entry_price || 0).toFixed(2)}</span>
                        </div>
                      </div>
                      <div className="trade-exec-right">
                        <span className={`trade-pnl ${isPos ? 'positive' : 'negative'}`}>
                          {isPos ? '+' : '-'}₹{Math.abs(t.pnl || 0).toFixed(2)}
                        </span>
                        <span className="trade-time">
                          {formatISTDateTime(t.timestamp)}
                        </span>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
