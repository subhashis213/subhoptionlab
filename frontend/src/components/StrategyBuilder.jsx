import { useState } from 'react'

const SYMBOLS = ['BANKNIFTY', 'NIFTY', 'FINNIFTY']
const OPTION_TYPES = ['CE', 'PE']
const ACTIONS = ['SELL', 'BUY']
const STRIKE_SELECTIONS = [
  'ATM',
  'ITM-1', 'ITM-2', 'ITM-3', 'ITM-4', 'ITM-5',
  'OTM-1', 'OTM-2', 'OTM-3', 'OTM-4', 'OTM-5',
]

export default function StrategyBuilder({ strategy, setStrategy }) {
  const [newLeg, setNewLeg] = useState({
    option_type: 'CE',
    action: 'SELL',
    strike_selection: 'ATM',
    lots: 1,
    sl_percent: null,
    target_percent: null,
    trailing_sl: null,
    move_sl_to_cost: false,
  })

  const addLeg = () => {
    setStrategy({
      ...strategy,
      legs: [...strategy.legs, { ...newLeg }],
    })
  }

  const removeLeg = (index) => {
    setStrategy({
      ...strategy,
      legs: strategy.legs.filter((_, i) => i !== index),
    })
  }

  const updateLeg = (index, field, value) => {
    const updated = [...strategy.legs]
    updated[index] = { ...updated[index], [field]: value }
    setStrategy({ ...strategy, legs: updated })
  }

  // Quick strategy presets
  const presets = {
    'Short Straddle': [
      { option_type: 'CE', action: 'SELL', strike_selection: 'ATM', lots: 1, sl_percent: 25, target_percent: null, trailing_sl: null, move_sl_to_cost: false },
      { option_type: 'PE', action: 'SELL', strike_selection: 'ATM', lots: 1, sl_percent: 25, target_percent: null, trailing_sl: null, move_sl_to_cost: false },
    ],
    'Short Strangle': [
      { option_type: 'CE', action: 'SELL', strike_selection: 'OTM-2', lots: 1, sl_percent: 30, target_percent: null, trailing_sl: null, move_sl_to_cost: false },
      { option_type: 'PE', action: 'SELL', strike_selection: 'OTM-2', lots: 1, sl_percent: 30, target_percent: null, trailing_sl: null, move_sl_to_cost: false },
    ],
    'Iron Condor': [
      { option_type: 'CE', action: 'SELL', strike_selection: 'OTM-2', lots: 1, sl_percent: 30, target_percent: null, trailing_sl: null, move_sl_to_cost: false },
      { option_type: 'CE', action: 'BUY', strike_selection: 'OTM-4', lots: 1, sl_percent: null, target_percent: null, trailing_sl: null, move_sl_to_cost: false },
      { option_type: 'PE', action: 'SELL', strike_selection: 'OTM-2', lots: 1, sl_percent: 30, target_percent: null, trailing_sl: null, move_sl_to_cost: false },
      { option_type: 'PE', action: 'BUY', strike_selection: 'OTM-4', lots: 1, sl_percent: null, target_percent: null, trailing_sl: null, move_sl_to_cost: false },
    ],
    'Bull Call Spread': [
      { option_type: 'CE', action: 'BUY', strike_selection: 'ATM', lots: 1, sl_percent: null, target_percent: 50, trailing_sl: null, move_sl_to_cost: false },
      { option_type: 'CE', action: 'SELL', strike_selection: 'OTM-2', lots: 1, sl_percent: 30, target_percent: null, trailing_sl: null, move_sl_to_cost: false },
    ],
  }

  const applyPreset = (name) => {
    setStrategy({ ...strategy, legs: [...presets[name]] })
  }

  return (
    <div className="strategy-builder">
      <div className="section-header">
        <h2>Strategy Builder</h2>
      </div>

      {/* Symbol Selection */}
      <div className="form-group">
        <label>Index</label>
        <div className="btn-group">
          {SYMBOLS.map(s => (
            <button
              key={s}
              className={`btn-toggle ${strategy.symbol === s ? 'active' : ''}`}
              onClick={() => setStrategy({ ...strategy, symbol: s })}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Quick Presets */}
      <div className="form-group">
        <label>Quick Strategies</label>
        <div className="preset-grid">
          {Object.keys(presets).map(name => (
            <button
              key={name}
              className="btn-preset"
              onClick={() => applyPreset(name)}
            >
              {name}
            </button>
          ))}
        </div>
      </div>

      {/* Legs Table */}
      <div className="legs-section">
        <h3>Positions <span className="leg-count">{strategy.legs.length} legs</span></h3>

        {strategy.legs.length > 0 && (
          <div className="legs-table">
            <div className="legs-header">
              <span>Type</span>
              <span>Action</span>
              <span>Strike</span>
              <span>Lots</span>
              <span>SL%</span>
              <span>Target%</span>
              <span></span>
            </div>
            {strategy.legs.map((leg, i) => (
              <div key={i} className={`leg-row ${leg.action === 'SELL' ? 'sell' : 'buy'}`}>
                <select value={leg.option_type} onChange={e => updateLeg(i, 'option_type', e.target.value)}>
                  {OPTION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <select value={leg.action} onChange={e => updateLeg(i, 'action', e.target.value)}>
                  {ACTIONS.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
                <select value={leg.strike_selection} onChange={e => updateLeg(i, 'strike_selection', e.target.value)}>
                  {STRIKE_SELECTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <input
                  type="number"
                  min="1"
                  value={leg.lots}
                  onChange={e => updateLeg(i, 'lots', parseInt(e.target.value) || 1)}
                  className="input-narrow"
                />
                <input
                  type="number"
                  min="0"
                  step="5"
                  value={leg.sl_percent ?? ''}
                  placeholder="—"
                  onChange={e => updateLeg(i, 'sl_percent', e.target.value === '' ? null : parseFloat(e.target.value))}
                  className="input-narrow"
                />
                <input
                  type="number"
                  min="0"
                  step="5"
                  value={leg.target_percent ?? ''}
                  placeholder="—"
                  onChange={e => updateLeg(i, 'target_percent', e.target.value === '' ? null : parseFloat(e.target.value))}
                  className="input-narrow"
                />
                <button className="btn-remove" onClick={() => removeLeg(i)}>✕</button>
              </div>
            ))}
          </div>
        )}

        {strategy.legs.length === 0 && (
          <div className="empty-legs">
            <p>No positions added yet. Use a quick strategy above or add manually below.</p>
          </div>
        )}
      </div>

      {/* Add New Leg */}
      <div className="add-leg-section">
        <h3>Add Position</h3>
        <div className="add-leg-form">
          <select value={newLeg.option_type} onChange={e => setNewLeg({ ...newLeg, option_type: e.target.value })}>
            {OPTION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <select value={newLeg.action} onChange={e => setNewLeg({ ...newLeg, action: e.target.value })}>
            {ACTIONS.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
          <select value={newLeg.strike_selection} onChange={e => setNewLeg({ ...newLeg, strike_selection: e.target.value })}>
            {STRIKE_SELECTIONS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <input
            type="number"
            min="1"
            value={newLeg.lots}
            onChange={e => setNewLeg({ ...newLeg, lots: parseInt(e.target.value) || 1 })}
            className="input-narrow"
            placeholder="Lots"
          />
          <input
            type="number"
            min="0"
            step="5"
            value={newLeg.sl_percent ?? ''}
            onChange={e => setNewLeg({ ...newLeg, sl_percent: e.target.value === '' ? null : parseFloat(e.target.value) })}
            className="input-narrow"
            placeholder="SL%"
          />
          <input
            type="number"
            min="0"
            step="5"
            value={newLeg.target_percent ?? ''}
            onChange={e => setNewLeg({ ...newLeg, target_percent: e.target.value === '' ? null : parseFloat(e.target.value) })}
            className="input-narrow"
            placeholder="Target%"
          />
          <button className="btn-add" onClick={addLeg}>
            + Add Position
          </button>
        </div>
      </div>
    </div>
  )
}
