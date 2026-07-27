import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { X, Play, Clock, Activity } from 'lucide-react'
import { strategyApi } from '../api/client'
import useMarketStream from '../hooks/useMarketStream'

export default function QuickTradeModal({ tradeDetails, onClose, onExecute }) {
  const navigate = useNavigate()
  const [action, setAction] = useState('BUY')
  const [orderType, setOrderType] = useState('MARKET')
  const [limitPrice, setLimitPrice] = useState('')
  const [lots, setLots] = useState(1)
  const [executionTime, setExecutionTime] = useState('')
  const [slType, setSlType] = useState('points')
  const [slValue, setSlValue] = useState('')
  const [targetType, setTargetType] = useState('points')
  const [targetValue, setTargetValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const { strike, type, ltp: initialLtp, symbol, expiry, initialAction, instrument_key } = tradeDetails || {}

  // Subscribe to live WebSocket feed for this option/stock
  const rawKey = instrument_key ? instrument_key.replace(':', '|') : ''
  const liveData = useMarketStream(rawKey ? [rawKey] : [])
  const liveTick = rawKey ? liveData[rawKey] : null
  const liveLtp = liveTick ? (liveTick.ltp ?? liveTick.last_price ?? initialLtp) : (initialLtp || 0)

  // Update action when tradeDetails changes
  useEffect(() => {
    if (initialAction) {
      setAction(initialAction)
    }
  }, [initialAction])

  if (!tradeDetails) return null

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
      limit_price: orderType === 'LIMIT' ? (parseFloat(limitPrice) || Number(liveLtp) || 0) : 0,
      sl_type: slType,
      sl_value: parseFloat(slValue) || 0,
      target_type: targetType,
      target_value: parseFloat(targetValue) || 0,
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
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '440px' }}>
        <div className="modal-header">
          <h3>Quick Paper Trade</h3>
          <button className="btn-icon" onClick={onClose}><X size={20} /></button>
        </div>
        
        <div className="modal-body">
          {error && <div className="error-banner">{error}</div>}
          
          <div className="stat-card" style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '12px', padding: '16px' }}>
            <div className="stat-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{symbol}</span>
              <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--accent)', background: 'rgba(34, 197, 94, 0.12)', padding: '2px 8px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Activity size={12} className="pulse-icon" /> LIVE TICK
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
              <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 800 }}>{type === 'EQ' ? 'EQUITY' : `${strike} ${type}`}</h2>
              <span style={{ fontSize: '1.35rem', fontWeight: 'bold', color: 'var(--primary)' }}>₹{Number(liveLtp || 0).toFixed(2)}</span>
            </div>
          </div>

          <div className="form-group">
            <label style={{ fontWeight: 600, marginBottom: '6px', display: 'block' }}>Order Type</label>
            <div className="toggle-group">
              <button 
                type="button"
                className={`toggle-option ${orderType === 'MARKET' ? 'active' : ''}`}
                onClick={() => setOrderType('MARKET')}
                style={{ padding: '10px' }}
              >
                MARKET
              </button>
              <button 
                type="button"
                className={`toggle-option ${orderType === 'LIMIT' ? 'active' : ''}`}
                onClick={() => setOrderType('LIMIT')}
                style={{ padding: '10px' }}
              >
                LIMIT
              </button>
            </div>
          </div>

          {orderType === 'LIMIT' && (
            <div className="form-group">
              <label style={{ fontWeight: 600, marginBottom: '6px', display: 'block' }}>Limit Price</label>
              <input 
                type="number" 
                className="form-control" 
                value={limitPrice} 
                onChange={(e) => setLimitPrice(e.target.value)}
                placeholder={`e.g. ${(Number(liveLtp || 0) * 0.95).toFixed(2)}`}
              />
            </div>
          )}

          <div className="form-group">
            <label style={{ fontWeight: 600, marginBottom: '6px', display: 'block' }}>Action</label>
            <div className="toggle-group">
              <button 
                type="button"
                className={`toggle-option buy ${action === 'BUY' ? 'active' : ''}`}
                onClick={() => setAction('BUY')}
                style={{ padding: '12px', fontWeight: 700 }}
              >
                BUY
              </button>
              <button 
                type="button"
                className={`toggle-option sell ${action === 'SELL' ? 'active' : ''}`}
                onClick={() => setAction('SELL')}
                style={{ padding: '12px', fontWeight: 700 }}
              >
                SELL
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label style={{ fontWeight: 600, marginBottom: '6px', display: 'block' }}>{type === 'EQ' ? 'Quantity' : 'Lots'}</label>
              <div className="stepper" style={{ marginBottom: 0, height: '42px' }}>
                <button type="button" onClick={() => setLots(Math.max(1, lots - 1))}>-</button>
                <input 
                  type="number" 
                  value={lots} 
                  onChange={(e) => setLots(Math.max(1, parseInt(e.target.value) || 1))}
                  style={{ textAlign: 'center', background: 'transparent', height: '100%' }} 
                />
                <button type="button" onClick={() => setLots(lots + 1)}>+</button>
              </div>
            </div>
            
            <div className="form-group" style={{ flex: 1 }}>
              <label style={{ fontWeight: 600, marginBottom: '6px', display: 'block' }}>Auto-Trade Time</label>
              <input 
                type="time" 
                className="form-control"
                value={executionTime}
                onChange={(e) => setExecutionTime(e.target.value)}
                placeholder="Immediate"
                style={{ padding: '8px 12px', height: '42px', minHeight: '42px', width: '100%', borderRadius: '8px' }}
              />
            </div>
          </div>
          <p className="field-hint" style={{ marginTop: '-4px', marginBottom: '8px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>Leave time empty for immediate Market execution.</p>

          {/* SL & Target Inputs */}
          <div style={{ display: 'flex', gap: '16px' }}>
            <div className="form-group" style={{ flex: 1, margin: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <label style={{ margin: 0, fontSize: '0.85rem', fontWeight: 600 }}>Stop Loss</label>
                <div className="toggle-group" style={{ margin: 0, display: 'flex' }}>
                  <button type="button" className={`toggle-option ${slType === 'points' ? 'active' : ''}`} onClick={() => setSlType('points')} style={{ padding: '2px 6px', fontSize: '0.75rem' }}>Pts</button>
                  <button type="button" className={`toggle-option ${slType === 'percentage' ? 'active' : ''}`} onClick={() => setSlType('percentage')} style={{ padding: '2px 6px', fontSize: '0.75rem' }}>%</button>
                </div>
              </div>
              <input type="number" className="form-control" placeholder="0" value={slValue} onChange={(e) => setSlValue(e.target.value)} style={{ padding: '8px 12px', height: '40px' }} />
            </div>

            <div className="form-group" style={{ flex: 1, margin: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <label style={{ margin: 0, fontSize: '0.85rem', fontWeight: 600 }}>Target</label>
                <div className="toggle-group" style={{ margin: 0, display: 'flex' }}>
                  <button type="button" className={`toggle-option ${targetType === 'points' ? 'active' : ''}`} onClick={() => setTargetType('points')} style={{ padding: '2px 6px', fontSize: '0.75rem' }}>Pts</button>
                  <button type="button" className={`toggle-option ${targetType === 'percentage' ? 'active' : ''}`} onClick={() => setTargetType('percentage')} style={{ padding: '2px 6px', fontSize: '0.75rem' }}>%</button>
                </div>
              </div>
              <input type="number" className="form-control" placeholder="0" value={targetValue} onChange={(e) => setTargetValue(e.target.value)} style={{ padding: '8px 12px', height: '40px' }} />
            </div>
          </div>
          
        </div>

        <div className="modal-footer" style={{ display: 'flex', gap: '12px' }}>
          <button 
            type="button"
            className="btn-primary" 
            style={{ 
              width: '100%', 
              height: '46px',
              display: 'flex', 
              alignItems: 'center', 
              justify: 'center', 
              gap: '8px', 
              fontSize: '1rem',
              fontWeight: 700,
              background: action === 'BUY' ? 'var(--success)' : 'var(--danger)', 
              borderColor: action === 'BUY' ? 'var(--success)' : 'var(--danger)',
              borderRadius: '10px',
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
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
