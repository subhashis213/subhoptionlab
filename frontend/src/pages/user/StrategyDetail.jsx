/**
 * Strategy Detail — live position monitoring with real-time P&L.
 */
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { strategyApi } from '../../api/client'
import {
  ArrowLeft, ArrowRight, Activity, TrendingUp, TrendingDown,
  Shield, Clock, Edit3, Power, RefreshCw, XCircle, Trash2
} from 'lucide-react'
import BottomSheet from '../../components/BottomSheet'

const LOT_SIZES = { NIFTY: 75, BANKNIFTY: 15, FINNIFTY: 25, MIDCAPNIFTY: 50 }

export default function StrategyDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [strategy, setStrategy] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState('')
  const [showTimeEdit, setShowTimeEdit] = useState(false)
  const [editStartTime, setEditStartTime] = useState('')
  const [editEndTime, setEditEndTime] = useState('')

  useEffect(() => {
    loadStrategy()
    const interval = setInterval(loadStrategy, 1000) // Live refresh
    return () => clearInterval(interval)
  }, [id])

  // Listen for WebSocket updates
  useEffect(() => {
    const handler = (e) => {
      const msg = e.detail
      if (msg.strategy_id === id) {
        loadStrategy() // Refresh on any update for this strategy
      }
    }
    window.addEventListener('pt-ws-message', handler)
    return () => window.removeEventListener('pt-ws-message', handler)
  }, [id])

  const loadStrategy = async () => {
    try {
      const data = await strategyApi.get(id)
      setStrategy(data)
    } catch (err) {
      console.error(err)
    }
    setLoading(false)
  }

  const handleExitLeg = async (legId) => {
    setActionLoading(legId)
    try {
      await strategyApi.exitLeg(id, legId)
      await loadStrategy()
    } catch (err) {
      alert(err.message)
    }
    setActionLoading('')
  }

  const handleExitAll = async () => {
    if (!confirm('Exit all open legs?')) return
    setActionLoading('all')
    try {
      await strategyApi.exitAll(id)
      await loadStrategy()
    } catch (err) {
      alert(err.message)
    }
    setActionLoading('')
  }

  const handleActivate = async () => {
    if (!confirm('Activate this strategy now? Market orders will be simulated at current LTP.')) return
    setActionLoading('activate')
    try {
      await strategyApi.activate(id)
      await loadStrategy()
    } catch (err) {
      alert(err.message)
    }
    setActionLoading('')
  }

  const handleReuse = async () => {
    if (!confirm('This will duplicate this strategy with next Thursday expiry and activate it for today. Proceed?')) return
    setActionLoading('reuse')
    try {
      const res = await strategyApi.reuse(id)
      navigate(`/strategies/${res.new_strategy_id}`)
    } catch (err) {
      alert(err.message)
    }
    setActionLoading('')
  }

  const openTimeEdit = () => {
    setEditStartTime(strategy.start_time || '')
    setEditEndTime(strategy.end_time || '')
    setShowTimeEdit(true)
  }

  const handleUpdateTime = async () => {
    setActionLoading('time')
    try {
      await strategyApi.updateTimes(id, {
        start_time: editStartTime,
        end_time: editEndTime
      })
      setShowTimeEdit(false)
      await loadStrategy()
    } catch (err) {
      alert(err.message)
    }
    setActionLoading('')
  }

  const handleDelete = async () => {
    if (!window.confirm("Are you sure you want to delete this strategy?")) return
    setActionLoading('delete')
    try {
      await strategyApi.delete(id)
      navigate('/strategies')
    } catch (err) {
      alert(err.message)
      setActionLoading('')
    }
  }

  if (loading) return <div className="page-loading"><div className="spinner" /></div>
  if (!strategy) return <div className="page"><p>Strategy not found</p></div>

  const openLegs = (strategy.legs || []).filter(l => l.current_status === 'open')
  const closedLegs = (strategy.legs || []).filter(l => l.current_status !== 'open')

  return (
    <div className="page">
      <div className="page-header compact">
        <button className="btn-back" onClick={() => navigate('/strategies')}>
          <ArrowLeft size={20} />
        </button>
        <div style={{ flex: 1 }}>
          <h2>{strategy.name}</h2>
          <span className={`badge badge-${strategy.status}`}>{strategy.status}</span>
        </div>
        {['draft', 'pending'].includes(strategy.status) && (
          <>
            <button
              className="btn-primary"
              onClick={handleActivate}
              disabled={actionLoading === 'activate' || actionLoading === 'delete'}
              style={{ padding: '8px 16px', minHeight: '36px', width: 'auto', marginRight: '8px' }}
            >
              {actionLoading === 'activate' ? '...' : <><Power size={16} /> Activate</>}
            </button>
            <button
              className="btn-danger-sm"
              onClick={handleDelete}
              disabled={actionLoading === 'delete' || actionLoading === 'activate'}
              style={{ padding: '8px 16px', minHeight: '36px', width: 'auto' }}
            >
              {actionLoading === 'delete' ? '...' : <><Trash2 size={16} /> Delete</>}
            </button>
          </>
        )}
      </div>

      {/* Strategy P&L Card */}
      <div className="pnl-card">
        <div className="pnl-card-content">
          <span className="pnl-label">Total P&L</span>
          <h2 className={`pnl-value ${(strategy.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
            {(strategy.total_pnl || 0) >= 0 ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
            ₹{Math.abs(strategy.total_pnl || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </h2>
        </div>
        <div className="pnl-meta">
          <span>{strategy.underlying}</span>
          <span>{openLegs.length} open / {(strategy.legs || []).length} total</span>
          {strategy.move_sl_to_cost && (
            <span className="msl-badge"><Shield size={12} /> SL→Cost</span>
          )}
        </div>
        <div className="pnl-meta" style={{ marginTop: '8px', borderTop: '1px solid var(--border)', paddingTop: '8px', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Clock size={14} className="text-muted" />
            <span className="text-muted" style={{ fontSize: '0.85rem' }}>
              {strategy.start_time || 'Manual'} - {strategy.end_time || 'Manual'}
            </span>
          </div>
          {['draft', 'pending'].includes(strategy.status) && (
            <button className="btn-icon text-muted" onClick={openTimeEdit} style={{ background: 'transparent', padding: '4px', minHeight: 'auto' }}>
              <Edit3 size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Open Legs */}
      {openLegs.length > 0 && (
        <div className="section">
          <div className="section-header">
            <h3>Open Positions</h3>
            {openLegs.length > 1 && strategy.status === 'active' && (
              <button
                className="btn-danger-sm"
                onClick={handleExitAll}
                disabled={actionLoading === 'all'}
              >
                <Power size={14} /> Exit All
              </button>
            )}
          </div>

          {openLegs.map((leg) => {
            const entry = leg.entry_price || 0
            const current = leg.current_ltp || entry
            const lotSize = LOT_SIZES[leg.symbol || strategy.underlying] || 50
            const totalQty = (leg.qty || 1) * lotSize
            const pnl = leg.side === 'BUY'
              ? (current - entry) * totalQty
              : (entry - current) * totalQty

            // SL/target distance
            const slDist = leg.current_sl_price
              ? Math.abs(current - leg.current_sl_price)
              : null
            const tgtDist = leg.current_target_price
              ? Math.abs(current - leg.current_target_price)
              : null

            return (
              <div key={leg._id} className={`position-card ${leg.side.toLowerCase()}`}>
                <div className="position-header">
                  <div className="position-info">
                    <span className={`side-badge ${leg.side.toLowerCase()}`}>{leg.side}</span>
                    <span className="position-symbol">
                      {leg.strike} {leg.option_type}
                    </span>
                    <span className="position-qty">{leg.qty}L ({totalQty})</span>
                  </div>
                  <button
                    className="btn-exit"
                    onClick={() => handleExitLeg(leg._id)}
                    disabled={!!actionLoading}
                  >
                    <XCircle size={16} /> Exit
                  </button>
                </div>

                <div className="position-prices">
                  <div className="price-item">
                    <span className="price-label">Entry</span>
                    <span className="price-value">{entry.toFixed(2)}</span>
                  </div>
                  <div className="price-item">
                    <span className="price-label">LTP</span>
                    <span className="price-value live">{current.toFixed(2)}</span>
                  </div>
                  <div className="price-item">
                    <span className="price-label">P&L</span>
                    <span className={`price-value ${pnl >= 0 ? 'positive' : 'negative'}`}>
                      ₹{pnl.toFixed(2)}
                    </span>
                  </div>
                </div>

                {/* SL/Target Progress */}
                <div className="sl-target-indicators">
                  {leg.current_sl_price && (
                    <div className="indicator sl">
                      <span>SL: {leg.current_sl_price.toFixed(2)}</span>
                      {slDist && <span className="dist">({slDist.toFixed(1)} away)</span>}
                    </div>
                  )}
                  {leg.current_target_price && (
                    <div className="indicator target">
                      <span>TGT: {leg.current_target_price.toFixed(2)}</span>
                      {tgtDist && <span className="dist">({tgtDist.toFixed(1)} away)</span>}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Closed Legs */}
      {closedLegs.length > 0 && (
        <div className="section">
          <div className="section-header">
            <h3>Closed Positions</h3>
          </div>
          {closedLegs.map((leg) => {
            const entry = leg.entry_price || 0
            const exit = leg.exit_price || entry
            const lotSize = LOT_SIZES[leg.symbol || strategy.underlying] || 50
            const totalQty = (leg.qty || 1) * lotSize
            const pnl = leg.side === 'BUY'
              ? (exit - entry) * totalQty
              : (entry - exit) * totalQty

            return (
              <div key={leg._id} className={`closed-leg-card ${leg.side.toLowerCase()}`}>
                <div className="closed-leg-header">
                  <div className="closed-leg-info">
                    <span className={`side-badge ${leg.side.toLowerCase()}`}>{leg.side}</span>
                    <span className="position-symbol">{leg.strike} {leg.option_type}</span>
                    <span className="position-qty">{leg.qty}L ({totalQty})</span>
                  </div>
                  {leg.exit_reason && (
                    <span className="exit-reason-badge">
                      {leg.exit_reason.replace('_', ' ')}
                    </span>
                  )}
                </div>
                <div className="closed-leg-prices">
                  <div className="price-item">
                    <span className="price-label">Entry</span>
                    <span className="price-value">{entry.toFixed(2)}</span>
                  </div>
                  <div className="price-item">
                    <span className="price-label">Exit</span>
                    <span className="price-value">{exit.toFixed(2)}</span>
                  </div>
                  <div className="price-item">
                    <span className="price-label">Realized P&L</span>
                    <span className={`price-value ${pnl >= 0 ? 'positive' : 'negative'}`}>
                      ₹{pnl.toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Time Edit Modal */}
      <BottomSheet
        isOpen={showTimeEdit}
        onClose={() => setShowTimeEdit(false)}
        title="Edit Strategy Timing"
      >
        <div className="form-group">
          <label>Start Time (HH:MM)</label>
          <input 
            type="time"
            value={editStartTime}
            onChange={(e) => setEditStartTime(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>End Time (HH:MM)</label>
          <input 
            type="time"
            value={editEndTime}
            onChange={(e) => setEditEndTime(e.target.value)}
          />
        </div>
        <div className="form-actions" style={{ marginTop: '16px' }}>
          <button 
            className="btn-primary btn-full"
            onClick={handleUpdateTime}
            disabled={actionLoading === 'time'}
          >
            {actionLoading === 'time' ? 'Saving...' : 'Save Timing'}
          </button>
        </div>
      </BottomSheet>
    </div>
  )
}
