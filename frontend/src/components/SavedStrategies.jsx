import { useState, useEffect } from 'react'

export default function SavedStrategies({ onLoad, apiBase, refreshCounter, setActiveTab }) {
  const [strategies, setStrategies] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchStrategies = async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await fetch(`${apiBase}/strategies`)
      if (!resp.ok) throw new Error('Failed to load saved strategies')
      const data = await resp.json()
      setStrategies(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStrategies()
  }, [apiBase, refreshCounter])

  const deleteStrategy = async (id, e) => {
    e.stopPropagation()
    if (!window.confirm('Delete this saved strategy?')) return
    try {
      await fetch(`${apiBase}/strategies/${id}`, { method: 'DELETE' })
      setStrategies(strategies.filter(s => s.id !== id))
    } catch (err) {
      alert('Failed to delete strategy')
    }
  }

  if (loading) {
    return (
      <div className="saved-strategies loading">
        <div className="spinner"></div>
        <p>Loading saved strategies...</p>
      </div>
    )
  }

  return (
    <div className="saved-strategies">
      <div className="section-header">
        <h2>Saved Strategies</h2>
        <button className="btn-refresh" onClick={fetchStrategies}>🔄 Refresh</button>
      </div>

      {error && <div className="error-banner">⚠ {error}</div>}

      {strategies.length === 0 && !error && (
        <div className="empty-state">
          <p>No strategies saved yet. Build a strategy and save it to quickly run tests later.</p>
        </div>
      )}

      <div className="strategies-grid">
        {strategies.map((item) => {
          const cfg = item.config || {}
          return (
            <div
              key={item.id}
              className="strategy-card"
              onClick={() => onLoad(cfg)}
            >
              <div className="card-top">
                <h3>{item.name || 'Unnamed Strategy'}</h3>
                <button className="btn-delete" onClick={(e) => deleteStrategy(item.id, e)}>✕</button>
              </div>
              
              <div className="card-meta">
                <span className="badge">{cfg.symbol || 'BANKNIFTY'}</span>
                <span className="meta-time">{cfg.entry_time || '09:20'} → {cfg.exit_time || '15:15'}</span>
              </div>

              <div className="card-legs">
                {cfg.legs && cfg.legs.map((leg, i) => (
                  <div key={i} className={`leg-chip ${leg.action === 'SELL' ? 'sell' : 'buy'}`}>
                    {leg.action} {leg.lots}L {leg.strike_selection} {leg.option_type}
                  </div>
                ))}
              </div>

              <div className="card-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="load-prompt">Click to load →</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
