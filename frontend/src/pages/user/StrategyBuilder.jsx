/**
 * Step-by-step mobile Strategy Builder.
 * Step 1: Strategy setup (name, underlying, move-SL-to-cost)
 * Step 2: Add legs (bottom sheet for each leg)
 * Step 3: Review & confirm
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { strategyApi, marketsApi } from '../../api/client'
import BottomSheet from '../../components/BottomSheet'
import {
  ArrowLeft, ArrowRight, Plus, Trash2, Edit3, Check,
  ChevronDown, ToggleLeft, ToggleRight, AlertTriangle
} from 'lucide-react'

const UNDERLYINGS = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCAPNIFTY']
const LOT_SIZES = { NIFTY: 75, BANKNIFTY: 15, FINNIFTY: 25, MIDCAPNIFTY: 50 }

export default function StrategyBuilder() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [strategy, setStrategy] = useState({
    name: '',
    underlying: 'NIFTY',
    move_sl_to_cost: false,
    entry_time: '',
    exit_time: '',
    legs: [],
  })
  const [showAddLeg, setShowAddLeg] = useState(false)
  const [editingLeg, setEditingLeg] = useState(null)
  const [legForm, setLegForm] = useState({
    symbol: 'NIFTY',
    expiry: _nextThursday(),
    strikeSelection: 'ATM',
    strike: 'ATM',
    option_type: 'CE',
    side: 'SELL',
    qty: 1,
    sl_type: 'points',
    sl_value: 0,
    target_type: 'points',
    target_value: 0,
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const [expiries, setExpiries] = useState([])

  useEffect(() => {
    marketsApi.expiries(strategy.underlying)
      .then(res => {
        setExpiries(res)
        if (res.length > 0 && !editingLeg) {
           setLegForm(prev => ({ ...prev, expiry: res[0] }))
        }
      })
      .catch(console.error)
  }, [strategy.underlying])

  function _defaultLeg(underlying) {
    return {
      symbol: underlying,
      expiry: (typeof expiries !== 'undefined' && expiries.length > 0) ? expiries[0] : _nextThursday(),
      strikeSelection: 'ATM', // Custom UI state
      strike: 'ATM',
      option_type: 'CE',
      side: 'SELL',
      qty: 1,
      sl_type: 'points',
      sl_value: 0,
      target_type: 'points',
      target_value: 0,
    }
  }

  function _nextThursday() {
    const d = new Date()
    const day = d.getDay()
    const diff = ((4 - day + 7) % 7) || 7
    d.setDate(d.getDate() + diff)
    return d.toISOString().split('T')[0]
  }

  const addLeg = () => {
    setLegForm(_defaultLeg(strategy.underlying))
    setEditingLeg(null)
    setShowAddLeg(true)
  }

  const editLeg = (index) => {
    setLegForm({ ...strategy.legs[index] })
    setEditingLeg(index)
    setShowAddLeg(true)
  }

  const removeLeg = (index) => {
    setStrategy({
      ...strategy,
      legs: strategy.legs.filter((_, i) => i !== index),
    })
  }

  const saveLeg = () => {
    const newLegs = [...strategy.legs]
    if (editingLeg !== null) {
      newLegs[editingLeg] = { ...legForm }
    } else {
      newLegs.push({ ...legForm })
    }
    setStrategy({ ...strategy, legs: newLegs })
    setShowAddLeg(false)
    setEditingLeg(null)
  }

  const handleSubmit = async (activateNow = true) => {
    setError('')
    setSubmitting(true)
    try {
      const result = await strategyApi.create(strategy)
      if (activateNow) {
        await strategyApi.activate(result.strategy_id)
      }
      navigate(`/strategies/${result.strategy_id}`)
    } catch (err) {
      setError(err.message)
    }
    setSubmitting(false)
  }

  return (
    <div className="page strategy-builder-page">
      {/* Step Indicator */}
      <div className="step-indicator">
        {[1, 2, 3].map((s) => (
          <div key={s} className={`step-dot ${step >= s ? 'active' : ''} ${step === s ? 'current' : ''}`}>
            {step > s ? <Check size={14} /> : s}
          </div>
        ))}
        <div className="step-line" style={{ width: `${((step - 1) / 2) * 100}%` }} />
      </div>

      {error && (
        <div className="error-banner">
          <AlertTriangle size={16} /> {error}
          <button onClick={() => setError('')}>✕</button>
        </div>
      )}

      {/* Step 1: Strategy Setup */}
      {step === 1 && (
        <div className="builder-step">
          <h2>Create Strategy</h2>
          <p className="step-desc">Set up your options strategy basics</p>

          <div className="form-group">
            <label>Strategy Name</label>
            <input
              type="text"
              placeholder="e.g., Iron Condor Weekly"
              value={strategy.name}
              onChange={(e) => setStrategy({ ...strategy, name: e.target.value })}
              className="input-large"
            />
          </div>

          <div className="form-group toggle-row">
            <div>
              <label>Move SL to Cost</label>
              <p className="field-hint">
                If any leg's SL is hit, move all other legs' SL to their entry price (breakeven)
              </p>
            </div>
            <button
              className="toggle-btn"
              onClick={() => setStrategy({ ...strategy, move_sl_to_cost: !strategy.move_sl_to_cost })}
            >
              {strategy.move_sl_to_cost ?
                <ToggleRight size={32} className="toggle-on" /> :
                <ToggleLeft size={32} className="toggle-off" />
              }
            </button>
          </div>

          <div className="form-row" style={{ display: 'flex', gap: '12px', marginTop: '16px', marginBottom: '16px' }}>
            <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
              <label>Entry Time (Optional)</label>
              <input
                type="time"
                value={strategy.entry_time || ''}
                onChange={(e) => setStrategy({ ...strategy, entry_time: e.target.value })}
                className="input-large"
              />
            </div>
            <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
              <label>Exit Time (Optional)</label>
              <input
                type="time"
                value={strategy.exit_time || ''}
                onChange={(e) => setStrategy({ ...strategy, exit_time: e.target.value })}
                className="input-large"
              />
            </div>
          </div>

          <div className="form-group">
            <label>Underlying Index</label>
            <div className="chip-group">
              {UNDERLYINGS.map((u) => (
                <button
                  key={u}
                  className={`chip ${strategy.underlying === u ? 'active' : ''}`}
                  onClick={() => setStrategy({ ...strategy, underlying: u })}
                >
                  {u}
                  <span className="chip-sub">Lot: {LOT_SIZES[u]}</span>
                </button>
              ))}
            </div>
          </div>


          <div className="step-actions">
            <button className="btn-secondary" onClick={() => navigate(-1)}>
              <ArrowLeft size={16} /> Cancel
            </button>
            <button
              className="btn-primary"
              disabled={!strategy.name.trim()}
              onClick={() => setStep(2)}
            >
              Next <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Add Legs */}
      {step === 2 && (
        <div className="builder-step">
          <h2>Add Strategy Legs</h2>
          <p className="step-desc">
            {strategy.underlying} · {strategy.name}
          </p>

          {strategy.legs.length === 0 ? (
            <div className="empty-state">
              <p>No legs added yet. Add at least one leg.</p>
            </div>
          ) : (
            <div className="leg-cards">
              {strategy.legs.map((leg, i) => (
                <div key={i} className={`leg-card ${leg.side === 'BUY' ? 'buy' : 'sell'}`}>
                  <div className="leg-card-header">
                    <span className="leg-number">Leg {i + 1}</span>
                    <div className="leg-card-actions">
                      <button onClick={() => editLeg(i)}><Edit3 size={16} /></button>
                      <button onClick={() => removeLeg(i)}><Trash2 size={16} /></button>
                    </div>
                  </div>
                  <div className="leg-card-body">
                    <div className="leg-info-row">
                      <span className={`side-badge ${leg.side.toLowerCase()}`}>{leg.side}</span>
                      <span>{leg.symbol} {leg.strike} {leg.option_type}</span>
                      <span>{leg.qty} lot{leg.qty > 1 ? 's' : ''}</span>
                    </div>
                    <div className="leg-info-row secondary">
                      <span>Expiry: {leg.expiry}</span>
                    </div>
                    <div className="leg-sl-target">
                      {leg.sl_value > 0 && (
                        <span className="sl-badge">SL: {leg.sl_value} {leg.sl_type === 'points' ? 'pts' : '%'}</span>
                      )}
                      {leg.target_value > 0 && (
                        <span className="target-badge">TGT: {leg.target_value} {leg.target_type === 'points' ? 'pts' : '%'}</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <button className="add-leg-btn" onClick={addLeg}>
            <Plus size={18} /> Add Leg
          </button>

          <div className="step-actions">
            <button className="btn-secondary" onClick={() => setStep(1)}>
              <ArrowLeft size={16} /> Back
            </button>
            <button
              className="btn-primary"
              disabled={strategy.legs.length === 0}
              onClick={() => setStep(3)}
            >
              Review <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Review & Confirm */}
      {step === 3 && (
        <div className="builder-step">
          <h2>Review Strategy</h2>
          <p className="step-desc">Confirm your strategy details before activating</p>

          <div className="review-card">
            <div className="review-row">
              <span>Strategy Name</span>
              <strong>{strategy.name}</strong>
            </div>
            <div className="review-row">
              <span>Underlying Symbol</span>
              <strong>{strategy.underlying}</strong>
            </div>
            <div className="review-row">
              <span>Move SL to Cost</span>
              <strong>{strategy.move_sl_to_cost ? '✅ Enabled' : '❌ Disabled'}</strong>
            </div>
            <div className="review-row">
              <span>Total Legs</span>
              <strong>{strategy.legs.length} Leg{strategy.legs.length > 1 ? 's' : ''}</strong>
            </div>
          </div>

          <h3 className="section-title">Legs Summary</h3>
          {strategy.legs.map((leg, i) => (
            <div key={i} className={`review-leg ${leg.side.toLowerCase()}`}>
              <div className="review-leg-main">
                <span className={`side-badge ${leg.side.toLowerCase()}`}>{leg.side}</span>
                <span className="leg-strike-title">{leg.strike} {leg.option_type}</span>
                <span className="leg-qty-tag">{leg.qty} Lot{leg.qty > 1 ? 's' : ''} ({leg.qty * LOT_SIZES[strategy.underlying]} Qty)</span>
              </div>
              <div className="review-leg-sl">
                {leg.sl_value > 0 && <span className="sl-badge">SL: {leg.sl_value}{leg.sl_type === 'percentage' ? '%' : ' pts'}</span>}
                {leg.target_value > 0 && <span className="tgt-badge">TGT: {leg.target_value}{leg.target_type === 'percentage' ? '%' : ' pts'}</span>}
              </div>
            </div>
          ))}

          <div className="step-actions">
            <button className="btn-secondary" onClick={() => setStep(2)}>
              <ArrowLeft size={16} /> Back to Edit Legs
            </button>
          </div>
        </div>
      )}

      {/* Sticky Confirm Button (Step 3) */}
      {step === 3 && (
        <div className="sticky-bottom">
          <div className="sticky-bottom-content">
            <button
              className="btn-secondary btn-full"
              disabled={submitting}
              onClick={() => handleSubmit(false)}
            >
              {submitting ? 'Saving...' : '💾 Save as Draft'}
            </button>
            <button
              className="btn-primary btn-full"
              disabled={submitting}
              onClick={() => handleSubmit(true)}
            >
              {submitting ? 'Activating...' : '✅ Activate Now'}
            </button>
          </div>
        </div>
      )}

      {/* Add/Edit Leg Bottom Sheet */}
      <BottomSheet
        isOpen={showAddLeg}
        onClose={() => setShowAddLeg(false)}
        title={editingLeg !== null ? `Edit Leg ${editingLeg + 1}` : 'Add New Leg'}
      >
        <div className="leg-form">
          <div className="form-group">
            <label>Expiry Date</label>
            <select
              value={legForm.expiry}
              onChange={(e) => setLegForm({ ...legForm, expiry: e.target.value })}
              className="input-large"
            >
              {expiries.length > 0 ? expiries.map(exp => (
                <option key={exp} value={exp}>{exp}</option>
              )) : (
                <option value={legForm.expiry}>{legForm.expiry}</option>
              )}
            </select>
          </div>

          <div className="form-group">
            <label>Strike Selection</label>
            <select
              value={legForm.strikeSelection}
              onChange={(e) => {
                const val = e.target.value;
                setLegForm({ 
                  ...legForm, 
                  strikeSelection: val,
                  strike: val === 'FIXED' ? (strategy.underlying === 'BANKNIFTY' ? 52000 : 24000) : val 
                })
              }}
              className="input-large"
            >
              <option value="ATM">ATM (At The Money)</option>
              <option value="ITM1">ITM 1</option>
              <option value="ITM2">ITM 2</option>
              <option value="ITM3">ITM 3</option>
              <option value="OTM1">OTM 1</option>
              <option value="OTM2">OTM 2</option>
              <option value="OTM3">OTM 3</option>
              <option value="FIXED">Custom Fixed Strike</option>
            </select>
          </div>

          {legForm.strikeSelection === 'FIXED' && (
            <div className="form-group">
              <label>Fixed Strike Price</label>
              <input
                type="number"
                value={legForm.strike}
                onChange={(e) => setLegForm({ ...legForm, strike: parseFloat(e.target.value) || 0 })}
                step={strategy.underlying === 'BANKNIFTY' ? 100 : 50}
                className="input-large"
              />
            </div>
          )}

          <div className="form-group">
            <label>Option Type</label>
            <div className="toggle-group">
              <button
                className={`toggle-option ${legForm.option_type === 'CE' ? 'active' : ''}`}
                onClick={() => setLegForm({ ...legForm, option_type: 'CE' })}
              >
                CE (Call)
              </button>
              <button
                className={`toggle-option ${legForm.option_type === 'PE' ? 'active' : ''}`}
                onClick={() => setLegForm({ ...legForm, option_type: 'PE' })}
              >
                PE (Put)
              </button>
            </div>
          </div>

          <div className="form-group">
            <label>Side</label>
            <div className="toggle-group">
              <button
                className={`toggle-option buy ${legForm.side === 'BUY' ? 'active' : ''}`}
                onClick={() => setLegForm({ ...legForm, side: 'BUY' })}
              >
                BUY
              </button>
              <button
                className={`toggle-option sell ${legForm.side === 'SELL' ? 'active' : ''}`}
                onClick={() => setLegForm({ ...legForm, side: 'SELL' })}
              >
                SELL
              </button>
            </div>
          </div>

          <div className="form-group">
            <label>Lots</label>
            <div className="stepper">
              <button onClick={() => setLegForm({ ...legForm, qty: Math.max(1, legForm.qty - 1) })}>−</button>
              <span>{legForm.qty}</span>
              <button onClick={() => setLegForm({ ...legForm, qty: legForm.qty + 1 })}>+</button>
            </div>
            <p className="field-hint">= {legForm.qty * LOT_SIZES[strategy.underlying]} total quantity</p>
          </div>

          {/* SL Config */}
          <div className="sl-target-section">
            <h4>Stop Loss</h4>
            <div className="form-group">
              <div className="toggle-group small">
                <button
                  className={`toggle-option ${legForm.sl_type === 'points' ? 'active' : ''}`}
                  onClick={() => setLegForm({ ...legForm, sl_type: 'points' })}
                >
                  Points
                </button>
                <button
                  className={`toggle-option ${legForm.sl_type === 'percentage' ? 'active' : ''}`}
                  onClick={() => setLegForm({ ...legForm, sl_type: 'percentage' })}
                >
                  Percentage
                </button>
              </div>
              <input
                type="number"
                placeholder={legForm.sl_type === 'points' ? 'SL distance in points' : 'SL percentage (e.g. 15)'}
                value={legForm.sl_value || ''}
                onChange={(e) => setLegForm({ ...legForm, sl_value: parseFloat(e.target.value) || 0 })}
                min="0"
                step="0.5"
              />
            </div>
          </div>

          {/* Target Config */}
          <div className="sl-target-section">
            <h4>Target</h4>
            <div className="form-group">
              <div className="toggle-group small">
                <button
                  className={`toggle-option ${legForm.target_type === 'points' ? 'active' : ''}`}
                  onClick={() => setLegForm({ ...legForm, target_type: 'points' })}
                >
                  Points
                </button>
                <button
                  className={`toggle-option ${legForm.target_type === 'percentage' ? 'active' : ''}`}
                  onClick={() => setLegForm({ ...legForm, target_type: 'percentage' })}
                >
                  Percentage
                </button>
              </div>
              <input
                type="number"
                placeholder={legForm.target_type === 'points' ? 'Target distance in points' : 'Target percentage'}
                value={legForm.target_value || ''}
                onChange={(e) => setLegForm({ ...legForm, target_value: parseFloat(e.target.value) || 0 })}
                min="0"
                step="0.5"
              />
            </div>
          </div>

          <button className="btn-primary btn-full" onClick={saveLeg}>
            {editingLeg !== null ? 'Save Changes' : 'Add Leg'}
          </button>
        </div>
      </BottomSheet>
    </div>
  )
}
