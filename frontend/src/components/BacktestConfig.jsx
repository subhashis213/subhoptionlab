import { useState } from 'react'

export default function BacktestConfig({ strategy, setStrategy, config, setConfig, onRun, loading, dataInfo, onSaveStrategy }) {
  const [strategyName, setStrategyName] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const getMaxDate = () => {
    if (dataInfo?.to_date) return dataInfo.to_date
    if (dataInfo?.options) {
      const sym = strategy?.symbol || 'BANKNIFTY'
      const opt = dataInfo.options[sym] || Object.values(dataInfo.options)[0]
      if (opt?.max_date) return opt.max_date
    }
    return '2026-07-21'
  }

  const maxDate = getMaxDate()

  const datePresets = [
    { 
      label: '★ Latest Data (Jul 2026 - Today)', 
      from: '2026-07-01', 
      to: maxDate
    },
    { label: 'Jul 2024 Benchmark', from: '2024-07-15', to: '2024-07-19' },
    { label: '1W', days: 7 },
    { label: '1M', days: 30 },
    { label: '3M', days: 90 },
    { label: '6M', days: 180 },
    { label: '1Y', days: 365 },
  ]

  const applyPreset = (preset) => {
    if (preset.from && preset.to) {
      setConfig({ ...config, date_from: preset.from, date_to: preset.to })
      return
    }
    const maxDateStr = getMaxDate()
    const to = new Date(maxDateStr)
    const from = new Date(to.getTime() - preset.days * 24 * 60 * 60 * 1000)
    setConfig({
      ...config,
      date_from: from.toISOString().split('T')[0],
      date_to: to.toISOString().split('T')[0],
    })
  }

  const handleSaveClick = async () => {
    if (!strategyName.trim()) {
      alert('Please enter a name for your strategy')
      return
    }
    setIsSaving(true)
    setSaveSuccess(false)
    const success = await onSaveStrategy(strategyName)
    setIsSaving(false)
    if (success) {
      setSaveSuccess(true)
      setStrategyName('')
      setTimeout(() => setSaveSuccess(false), 3000)
    }
  }

  return (
    <div className="backtest-config">
      <div className="section-header">
        <h2>Backtest Settings</h2>
      </div>

      {/* Entry/Exit Time */}
      <div className="form-row">
        <div className="form-group">
          <label>Entry Time</label>
          <input
            type="time"
            step="1"
            value={strategy.entry_time}
            onChange={e => setStrategy({ ...strategy, entry_time: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label>Exit Time</label>
          <input
            type="time"
            step="1"
            value={strategy.exit_time}
            onChange={e => setStrategy({ ...strategy, exit_time: e.target.value })}
          />
        </div>
      </div>

      {/* ATM Basis */}
      <div className="form-group">
        <label>ATM Basis</label>
        <div className="btn-group">
          <button
            className={`btn-toggle ${!strategy.use_futures_for_atm ? 'active' : ''}`}
            onClick={() => setStrategy({ ...strategy, use_futures_for_atm: false })}
          >
            Spot
          </button>
          <button
            className={`btn-toggle ${strategy.use_futures_for_atm ? 'active' : ''}`}
            onClick={() => setStrategy({ ...strategy, use_futures_for_atm: true })}
          >
            Futures
          </button>
        </div>
      </div>

      {/* Expiry Mode */}
      <div className="form-group">
        <label>Expiry</label>
        <div className="btn-group">
          <button
            className={`btn-toggle ${strategy.expiry_mode === 'same_day' ? 'active' : ''}`}
            onClick={() => setStrategy({ ...strategy, expiry_mode: 'same_day' })}
          >
            Current Week
          </button>
          <button
            className={`btn-toggle ${strategy.expiry_mode === 'next_day' ? 'active' : ''}`}
            onClick={() => setStrategy({ ...strategy, expiry_mode: 'next_day' })}
          >
            Next Week
          </button>
        </div>
      </div>

      {/* Mode */}
      <div className="form-group">
        <label>Mode</label>
        <div className="btn-group">
          <button
            className={`btn-toggle ${strategy.mode === 'intraday' ? 'active' : ''}`}
            onClick={() => setStrategy({ ...strategy, mode: 'intraday' })}
          >
            Intraday
          </button>
          <button
            className={`btn-toggle ${strategy.mode === 'positional' ? 'active' : ''}`}
            onClick={() => setStrategy({ ...strategy, mode: 'positional' })}
          >
            Positional
          </button>
        </div>
      </div>

      {/* Strategy Level SL/TP */}
      <div className="form-row">
        <div className="form-group">
          <label>Strategy SL (pts)</label>
          <input
            type="number"
            min="0"
            step="10"
            value={strategy.strategy_sl_points || ''}
            placeholder="None"
            onChange={e => setStrategy({
              ...strategy,
              strategy_sl_points: e.target.value ? parseFloat(e.target.value) : null,
            })}
          />
        </div>
        <div className="form-group">
          <label>Strategy Target (pts)</label>
          <input
            type="number"
            min="0"
            step="10"
            value={strategy.strategy_target_points || ''}
            placeholder="None"
            onChange={e => setStrategy({
              ...strategy,
              strategy_target_points: e.target.value ? parseFloat(e.target.value) : null,
            })}
          />
        </div>
      </div>

      <hr className="divider" />

      {/* Save Strategy Option Box */}
      <div className="save-strategy-box">
        <h4>💾 Save Strategy Template</h4>
        <div className="save-strategy-row">
          <input
            type="text"
            placeholder="e.g. BN 09:56 Straddle SL25%"
            value={strategyName}
            onChange={e => setStrategyName(e.target.value)}
            disabled={isSaving}
          />
          <button
            className="btn-save-strategy"
            onClick={handleSaveClick}
            disabled={isSaving || strategy.legs.length === 0}
          >
            {isSaving ? 'Saving...' : '💾 Save'}
          </button>
        </div>
        {saveSuccess && (
          <p style={{ color: 'var(--profit)', fontSize: '0.82rem', marginTop: '0.5rem', fontWeight: 600 }}>
            ✅ Strategy saved! Check the Saved Strategies tab.
          </p>
        )}
      </div>

      {/* Date Range & Available History */}
      <div className="form-group">
        <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Date Range</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--primary)', fontWeight: 'normal' }}>📅 Click row below to auto-fill</span>
        </label>

        {dataInfo && dataInfo.options && (
          <div className="data-availability-card">
            <div className="avail-header">
              <span>🗄️ Available Data in Database</span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>From Year ➔ To Date</span>
            </div>
            <div className="avail-grid">
              {['BANKNIFTY', 'NIFTY', 'FINNIFTY'].map(sym => {
                const opt = dataInfo.options[sym]
                if (!opt) return null
                const isSelected = strategy.symbol === sym
                return (
                  <div
                    key={sym}
                    className={`avail-item ${isSelected ? 'active-avail' : ''}`}
                    onClick={() => setConfig({ ...config, date_from: opt.min_date, date_to: opt.max_date })}
                    title={`Click to set date range to full available history for ${sym}`}
                  >
                    <div className="avail-sym-row">
                      <strong>{sym}</strong>
                      {isSelected && <span className="avail-badge">Selected Index</span>}
                    </div>
                    <div className="avail-dates">
                      {opt.min_date} ➔ {opt.max_date}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        <div className="date-presets">
          {datePresets.map(p => (
            <button key={p.label} className="btn-date-preset" onClick={() => applyPreset(p)}>
              {p.label}
            </button>
          ))}
        </div>
        <div className="form-row" style={{ marginTop: '0.5rem' }}>
          <input
            type="date"
            value={config.date_from}
            onChange={e => setConfig({ ...config, date_from: e.target.value })}
          />
          <span className="date-sep">→</span>
          <input
            type="date"
            value={config.date_to}
            onChange={e => setConfig({ ...config, date_to: e.target.value })}
          />
        </div>
      </div>

      {/* Run Button */}
      <button
        className="btn-run"
        onClick={onRun}
        disabled={loading || strategy.legs.length === 0}
      >
        {loading ? (
          <><span className="spin">⟳</span> Running Backtest...</>
        ) : (
          <><span>▶</span> Run Backtest</>
        )}
      </button>
    </div>
  )
}
