/**
 * Strategy List — shows active, draft, and closed strategies.
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { strategyApi } from '../../api/client'
import { Plus, Trash2, Power } from 'lucide-react'

export default function StrategyList() {
  const navigate = useNavigate()
  const [strategies, setStrategies] = useState([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStrategies(true)
    const interval = setInterval(() => loadStrategies(false), 1000)
    return () => clearInterval(interval)
  }, [filter])

  // Listen for WebSocket updates
  useEffect(() => {
    const handler = () => {
      loadStrategies(false)
    }
    window.addEventListener('pt-ws-message', handler)
    return () => window.removeEventListener('pt-ws-message', handler)
  }, [filter])

  const loadStrategies = async (showLoading = false) => {
    if (showLoading) setLoading(true)
    try {
      const data = await strategyApi.list(filter || undefined)
      setStrategies(data.strategies || [])
    } catch (err) {
      console.error(err)
    }
    if (showLoading) setLoading(false)
  }

  const handleDelete = async (e, id, status) => {
    e.stopPropagation()
    if (status === 'active') {
      alert('Cannot delete an active strategy. Please close it first.')
      return
    }
    if (!confirm('Are you sure you want to delete this strategy?')) return
    
    try {
      await strategyApi.delete(id)
      setStrategies(strategies.filter(s => s._id !== id))
    } catch (err) {
      alert(err.message)
    }
  }

  const handleClose = async (e, id) => {
    e.stopPropagation()
    if (!confirm('Are you sure you want to completely close this active strategy?')) return
    
    try {
      await strategyApi.close(id)
      loadStrategies() // reload list to show it as closed
    } catch (err) {
      alert(err.message)
    }
  }

  const statusColors = {
    active: 'badge-active',
    draft: 'badge-draft',
    closed: 'badge-closed',
    pending: 'badge-pending'
  }

  return (
    <div className="page">
      <div className="page-header">
        <h2>Strategies</h2>
        <button className="btn-icon-primary" onClick={() => navigate('/strategies/new')}>
          <Plus size={20} />
        </button>
      </div>

      {/* Filter Chips */}
      <div className="filter-chips">
        {['', 'active', 'draft', 'closed'].map((f) => (
          <button
            key={f}
            className={`chip ${filter === f ? 'active' : ''}`}
            onClick={() => setFilter(f)}
          >
            {f || 'All'}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="page-loading"><div className="spinner" /></div>
      ) : strategies.length === 0 ? (
        <div className="empty-state">
          <p>No strategies found</p>
          <button className="btn-primary" onClick={() => navigate('/strategies/new')}>
            Create Strategy
          </button>
        </div>
      ) : (
        <div className="strategy-cards">
          {strategies.map((s) => (
            <div
              key={s._id}
              className="strategy-card"
              onClick={() => navigate(`/strategies/${s._id}`)}
            >
              <div className="strategy-card-header">
                <h4>{s.name}</h4>
                <span className={`badge ${statusColors[s.status] || ''}`}>{s.status}</span>
              </div>
              <div className="strategy-card-body">
                <span className="strategy-underlying">{s.underlying}</span>
                <span className="strategy-legs">{s.open_legs || 0}/{s.total_legs || 0} legs</span>
                <span className="strategy-date">
                  {new Date(s.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                </span>
              </div>
              <div className="strategy-card-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className={`strategy-pnl ${(s.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                  ₹{(s.total_pnl || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {s.status === 'active' ? (
                    <button 
                      className="btn-icon" 
                      onClick={(e) => handleClose(e, s._id)}
                      style={{ background: 'transparent', padding: '4px', minHeight: 'auto', color: 'var(--loss)' }}
                      title="Close Strategy"
                    >
                      <Power size={18} />
                    </button>
                  ) : (
                    <button 
                      className="btn-icon text-muted" 
                      onClick={(e) => handleDelete(e, s._id, s.status)}
                      style={{ background: 'transparent', padding: '4px', minHeight: 'auto' }}
                      title="Delete Strategy"
                    >
                      <Trash2 size={18} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
