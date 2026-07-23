import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import StrategyBuilder from '../../components/StrategyBuilder'
import BacktestConfig from '../../components/BacktestConfig'
import ResultsDashboard from '../../components/ResultsDashboard'
import SavedStrategies from '../../components/SavedStrategies'
import '../../App.css'

const getApiBase = () => {
  let url = import.meta.env.VITE_API_URL || '';
  url = url.replace(/\/+$/, '') + '/api'; // strip trailing slashes
  if (!url.endsWith('/api')) {
    url += '/api'
  }
  return url
}
const API_BASE = getApiBase()

function Backtester() {
  const navigate = useNavigate()
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('opti_theme') || 'dark'
  })
  const [activeTab, setActiveTab] = useState('builder')
  const [strategy, setStrategy] = useState({
    symbol: 'BANKNIFTY',
    legs: [],
    entry_time: '09:56:00',
    exit_time: '14:50:00',
    expiry_mode: 'same_day',
    use_futures_for_atm: false,
    strategy_sl_points: null,
    strategy_target_points: null,
    protect_profits: null,
    mode: 'intraday',
  })
  const [backtestConfig, setBacktestConfig] = useState({
    date_from: '2026-07-01',
    date_to: '2026-07-21',
  })
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [dataInfo, setDataInfo] = useState(null)
  const [refreshSavedCounter, setRefreshSavedCounter] = useState(0)

  // Apply dark/light theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('opti_theme', theme)
  }, [theme])

  // Fetch data availability on mount
  useEffect(() => {
    fetch(`${API_BASE}/data/stats`)
      .then(r => r.json())
      .then(info => {
        setDataInfo(info)
        const firstOpt = info?.options && Object.values(info.options)[0]
        if (firstOpt && firstOpt.max_date) {
          setBacktestConfig({
            date_from: '2026-07-01',
            date_to: firstOpt.max_date,
          })
        }
      })
      .catch(() => {})
  }, [])

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }

  const handleSaveStrategy = async (strategyName) => {
    if (!strategyName || strategyName.trim() === '') {
      alert('Please enter a name for your strategy')
      return false
    }
    if (strategy.legs.length === 0) {
      alert('Add at least one position before saving the strategy')
      return false
    }
    try {
      const resp = await fetch(`${API_BASE}/strategies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: strategyName.trim(),
          config: strategy,
        }),
      })
      if (!resp.ok) throw new Error('Failed to save strategy')
      setRefreshSavedCounter(c => c + 1)
      return true
    } catch (e) {
      alert(`Error saving strategy: ${e.message}`)
      return false
    }
  }

  const runBacktest = async () => {
    if (strategy.legs.length === 0) {
      setError('Add at least one position to the strategy before running backtest')
      return
    }
    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const resp = await fetch(`${API_BASE}/backtest/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategy_config: strategy,
          date_from: backtestConfig.date_from,
          date_to: backtestConfig.date_to,
        }),
      })
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}))
        throw new Error(errData.detail || `Backend server error (${resp.status}). Verify VITE_API_URL settings.`)
      }
      const { run_id } = await resp.json()

      let status = 'queued'
      let attempts = 0
      while (status !== 'completed' && status !== 'failed') {
        if (attempts++ > 240) {
          throw new Error('Backtest simulation timed out (120s). Please verify your Render backend container is running and populated.')
        }
        await new Promise(r => setTimeout(r, 500))
        const statusResp = await fetch(`${API_BASE}/backtest/${run_id}/status`)
        if (!statusResp.ok) throw new Error('Lost connection to backtest service.')
        const statusData = await statusResp.json()
        status = statusData.status
        if (status === 'failed') {
          throw new Error(statusData.error || 'Backtest simulation failed on cloud server')
        }
      }

      const resultsResp = await fetch(`${API_BASE}/backtest/${run_id}/results`)
      const resultsData = await resultsResp.json()
      setResults(resultsData)
      setActiveTab('results')
    } catch (e) {
      setError(e.message || 'Failed to run backtest')
    } finally {
      setLoading(false)
    }
  }

  const loadStrategy = (config) => {
    setStrategy(config)
    setActiveTab('builder')
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <button 
              className="btn-secondary" 
              onClick={() => window.history.length > 2 ? navigate(-1) : window.close()} 
              style={{ padding: '8px', borderRadius: '8px', width: 'auto' }}
              title="Go Back"
            >
              <ArrowLeft size={20} />
            </button>
            <div className="logo">
              <span className="logo-icon swastik" title="Shubh Muhurt">卐</span>
              <h1 className="brand-title">शुभमुहूर्त</h1>
            </div>
          </div>
          <p className="tagline hide-on-mobile">Options Strategy Backtester & Precision Analytics</p>
        </div>
        <div className="header-right">
          <button className="theme-switch-btn" onClick={toggleTheme} title="Switch Dark / Light Theme">
            {theme === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode'}
          </button>
          {dataInfo && dataInfo.options && Object.keys(dataInfo.options).length > 0 && (
            <div className="data-badge">
              <span className="badge-dot"></span>
              Data loaded: {Object.keys(dataInfo.options).join(', ')}
            </div>
          )}
        </div>
      </header>

      <nav className="tab-nav">
        <button
          className={`tab-btn ${activeTab === 'builder' ? 'active' : ''}`}
          onClick={() => setActiveTab('builder')}
        >
          <span className="tab-icon">⚙️</span> Strategy Builder
        </button>
        <button
          className={`tab-btn ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
          disabled={!results}
        >
          <span className="tab-icon">📊</span> Results Dashboard
        </button>
        <button
          className={`tab-btn ${activeTab === 'saved' ? 'active' : ''}`}
          onClick={() => setActiveTab('saved')}
        >
          <span className="tab-icon">💾</span> Saved Strategies
        </button>
      </nav>

      <main className="app-main">
        {error && (
          <div className="error-banner">
            <span>⚠️ {error}</span>
            <button onClick={() => setError(null)}>✕</button>
          </div>
        )}

        {activeTab === 'builder' && (
          <div className="builder-layout">
            <div className="builder-panel">
              <StrategyBuilder
                strategy={strategy}
                setStrategy={setStrategy}
                onSaveStrategy={handleSaveStrategy}
              />
            </div>
            <div className="config-panel">
              <BacktestConfig
                strategy={strategy}
                setStrategy={setStrategy}
                config={backtestConfig}
                setConfig={setBacktestConfig}
                onRun={runBacktest}
                loading={loading}
                dataInfo={dataInfo}
                onSaveStrategy={handleSaveStrategy}
              />
            </div>
          </div>
        )}

        {activeTab === 'results' && results && (
          <ResultsDashboard results={results} />
        )}

        {activeTab === 'saved' && (
          <SavedStrategies
            onLoad={loadStrategy}
            apiBase={API_BASE}
            refreshCounter={refreshSavedCounter}
          />
        )}
      </main>

      {loading && (
        <div className="loading-overlay">
          <div className="spinner"></div>
          <p style={{ color: '#fff', fontWeight: 600, fontSize: '1.1rem' }}>Running exact 1-minute tick simulation...</p>
        </div>
      )}
    </div>
  )
}
export default Backtester
