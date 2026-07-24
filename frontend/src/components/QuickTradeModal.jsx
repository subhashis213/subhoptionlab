import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { X, Play, Clock } from 'lucide-react'
import { strategyApi } from '../api/client'

export default function QuickTradeModal({ tradeDetails, onClose, onExecute }) {
  const navigate = useNavigate()
  const [action, setAction] = useState('BUY')
  const [orderType, setOrderType] = useState('MARKET')
  const [limitPrice, setLimitPrice] = useState('')
  const [lots, setLots] = useState(1)
  const [executionTime, setExecutionTime] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  if (!tradeDetails) return null

  const { strike, type, ltp, symbol, expiry } = tradeDetails

  const handleExecute = async () => {
    setLoading(true)
    setError(null)
    
    // Create a strategy configuration based on the quick trade
    const leg = {
      symbol: symbol,
      expiry: expiry || '2026-07-23', // fallback just in case
      strike: parseFloat(strike),
      option_type: type,
      side: action,
      qty: parseInt(lots),
      order_type: orderType,
      limit_price: orderType === 'LIMIT' ? parseFloat(limitPrice) || 0 : 0,
      sl_type: 'points',
      sl_value: 0,
      target_type: 'points',
      target_value: 0,
      instrument_key: tradeDetails.instrument_key || null
    }
    
    let formattedTime = null
    if (executionTime) {
      formattedTime = executionTime + ':00' // HH:MM:00
    }

    const strategyData = {
      name: `Quick ${action} ${symbol} ${strike} ${type}`,
      underlying: symbol,
      move_sl_to_cost: false,
      entry_time: formattedTime,
      legs: [leg]
    }

    try {
      const res = await strategyApi.create(strategyData)
      
      // Instantly activate for a live market feel (fetches live LTP)
      if (!formattedTime) {
        try {
          await strategyApi.activate(res.strategy_id)
        } catch (activationErr) {
          // If activation fails (e.g. market closed), delete the draft and throw
          await strategyApi.delete(res.strategy_id).catch(() => {})
          throw activationErr
        }
      }

      if (onExecute) onExecute()
      onClose()
      navigate(`/strategies/${res.strategy_id}`)
    } catch (err) {
      setError(err.message || 'Failed to execute paper trade')
      console.error(err)
      setLoading(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose} style={{ zIndex: 100 }}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '400px' }}>
        <div className="modal-header">
          <h3>Quick Paper Trade</h3>
          <button className="btn-icon" onClick={onClose}><X size={20} /></button>
        </div>
        
        <div className="modal-body">
          {error && <div className="error-banner" style={{ marginBottom: '16px' }}>{error}</div>}
          
          <div className="stat-card" style={{ background: 'var(--bg)', marginBottom: '20px' }}>
            <div className="stat-header">
              <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>{symbol}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <h2 style={{ margin: '8px 0 0' }}>{strike} {type}</h2>
              <span style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>₹{ltp.toFixed(2)}</span>
            </div>
          </div>

          <div className="form-group">
            <label>Order Type</label>
            <div className="toggle-group">
              <button 
                className={`toggle-option ${orderType === 'MARKET' ? 'active' : ''}`}
                onClick={() => setOrderType('MARKET')}
                style={{ padding: '8px' }}
              >
                MARKET
              </button>
              <button 
                className={`toggle-option ${orderType === 'LIMIT' ? 'active' : ''}`}
                onClick={() => setOrderType('LIMIT')}
                style={{ padding: '8px' }}
              >
                LIMIT
              </button>
            </div>
          </div>

          {orderType === 'LIMIT' && (
            <div className="form-group">
              <label>Limit Price</label>
              <input 
                type="number" 
                className="form-control" 
                value={limitPrice} 
                onChange={(e) => setLimitPrice(e.target.value)}
                placeholder={`e.g. ${(ltp * 0.95).toFixed(2)}`}
              />
            </div>
          )}

          <div className="form-group">
            <label>Action</label>
            <div className="toggle-group">
              <button 
                className={`toggle-option buy ${action === 'BUY' ? 'active' : ''}`}
                onClick={() => setAction('BUY')}
                style={{ padding: '12px' }}
              >
                BUY
              </button>
              <button 
                className={`toggle-option sell ${action === 'SELL' ? 'active' : ''}`}
                onClick={() => setAction('SELL')}
                style={{ padding: '12px' }}
              >
                SELL
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '16px' }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Lots</label>
              <div className="stepper" style={{ marginBottom: 0 }}>
                <button type="button" onClick={() => setLots(Math.max(1, lots - 1))}>-</button>
                <input 
                  type="number" 
                  value={lots} 
                  onChange={(e) => setLots(Math.max(1, parseInt(e.target.value) || 1))}
                  style={{ textAlign: 'center', background: 'transparent' }} 
                />
                <button type="button" onClick={() => setLots(lots + 1)}>+</button>
              </div>
            </div>
            
            <div className="form-group" style={{ flex: 1 }}>
              <label>Auto-Trade Time</label>
              <input 
                type="time" 
                className="form-control"
                value={executionTime}
                onChange={(e) => setExecutionTime(e.target.value)}
                placeholder="Immediate"
                style={{ padding: '8px', minHeight: '48px', height: '100%' }}
              />
            </div>
          </div>
          <p className="field-hint" style={{ marginTop: '-8px', marginBottom: '16px' }}>Leave time empty for immediate Market execution.</p>
          
        </div>

        <div className="modal-footer" style={{ display: 'flex', gap: '12px' }}>
          <button 
            className="btn-primary" 
            style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', background: action === 'BUY' ? 'var(--success)' : 'var(--danger)', borderColor: action === 'BUY' ? 'var(--success)' : 'var(--danger)' }}
            onClick={handleExecute}
            disabled={loading}
          >
            {loading ? <div className="spinner small" /> : (executionTime ? <Clock size={18} /> : <Play size={18} />)}
            {executionTime ? 'Schedule Auto-Trade' : `Execute ${action}`}
          </button>
        </div>
      </div>
    </div>
  )
}
