/**
 * Admin Global View — view all strategies across the platform.
 */
import { useState, useEffect } from 'react'
import { adminApi } from '../../api/client'
import { Filter } from 'lucide-react'

export default function AdminGlobal() {
  const [strategies, setStrategies] = useState([])
  const [filter, setFilter] = useState('active')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStrategies()
  }, [filter])

  const loadStrategies = async () => {
    setLoading(true)
    try {
      const data = await adminApi.allStrategies({ status: filter || undefined })
      setStrategies(data.strategies || [])
    } catch (err) {
      console.error(err)
    }
    setLoading(false)
  }

  const statusColors = {
    active: 'badge-active',
    draft: 'badge-draft',
    closed: 'badge-closed',
  }

  return (
    <div className="page admin-page">
      <div className="page-header">
        <h2>Global Strategies</h2>
      </div>

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
      ) : (
        <div className="admin-strategy-list">
          {strategies.length === 0 ? (
            <div className="empty-state">No strategies found</div>
          ) : (
            strategies.map((s) => (
              <div key={s._id} className="admin-strategy-card">
                <div className="admin-strategy-header">
                  <div>
                    <h4>{s.name}</h4>
                    <span className="user-name">by {s.user_name}</span>
                  </div>
                  <span className={`badge ${statusColors[s.status]}`}>{s.status}</span>
                </div>
                
                <div className="admin-strategy-body">
                  <span>{s.underlying}</span>
                  <span>{s.open_legs}/{s.total_legs} open legs</span>
                </div>

                <div className="admin-strategy-footer">
                  <span className={`pnl ${(s.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                    ₹{(s.total_pnl || 0).toLocaleString('en-IN')}
                  </span>
                  <span className="date">
                    {new Date(s.created_at).toLocaleString('en-IN', {
                      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                    })}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
