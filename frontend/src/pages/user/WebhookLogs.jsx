import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { strategyApi } from '../../api/client'
import { ArrowLeft, CheckCircle, XCircle, Clock } from 'lucide-react'

export default function WebhookLogs() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [strategy, setStrategy] = useState(null)

  useEffect(() => {
    loadData()
  }, [id])

  const loadData = async () => {
    try {
      const [stratData, logData] = await Promise.all([
        strategyApi.get(id),
        fetch(`/api/webhook/logs/${id}`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('pt_token')}` }
        }).then(res => res.json())
      ])
      setStrategy(stratData)
      setLogs(logData)
    } catch (err) {
      console.error(err)
    }
    setLoading(false)
  }

  if (loading) return <div className="page-loading"><div className="spinner" /></div>

  return (
    <div className="page">
      <div className="page-header compact">
        <button className="btn-back" onClick={() => navigate(-1)}>
          <ArrowLeft size={20} />
        </button>
        <div style={{ flex: 1 }}>
          <h2>Webhook Logs</h2>
          <span className="text-muted" style={{ fontSize: '0.85rem' }}>{strategy?.name}</span>
        </div>
        <button className="btn-secondary" onClick={loadData} style={{ padding: '4px 8px' }}>
          Refresh
        </button>
      </div>

      <div className="section" style={{ padding: '0 8px' }}>
        {logs.length === 0 ? (
          <div className="empty-state">
            <p>No webhook signals received yet.</p>
          </div>
        ) : (
          logs.map(log => (
            <div key={log._id} style={{ background: '#1e1e1e', padding: '12px', borderRadius: '8px', marginBottom: '12px', border: '1px solid #333' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className={`side-badge ${log.action.toLowerCase()}`}>{log.action}</span>
                  <strong style={{ color: '#fff' }}>{log.symbol}</strong>
                  <span className="text-muted" style={{ fontSize: '0.8rem' }}>{log.timeframe}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {log.status === 'EXECUTED' && <CheckCircle size={14} color="#00ff00" />}
                  {log.status !== 'EXECUTED' && <XCircle size={14} color={log.status === 'LOGGED_ONLY' ? '#aaaaaa' : '#ff3333'} />}
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: log.status === 'EXECUTED' ? '#00ff00' : (log.status === 'LOGGED_ONLY' ? '#aaa' : '#ff3333') }}>
                    {log.status}
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.85rem' }}>
                <div>
                  <span className="text-muted">Entry: </span>
                  <span style={{ color: '#fff' }}>{log.entry_price}</span>
                </div>
                <div>
                  <span className="text-muted">SL: </span>
                  <span style={{ color: '#fff' }}>{log.sl_price || 'N/A'}</span>
                </div>
              </div>

              {log.reason && (
                <div style={{ fontSize: '0.8rem', color: '#ffb74d', background: '#332610', padding: '6px', borderRadius: '4px', marginBottom: '8px' }}>
                  {log.reason}
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: '#888' }}>
                <Clock size={12} />
                {new Date(log.created_at).toLocaleString()} (TV Time: {log.signal_time})
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
