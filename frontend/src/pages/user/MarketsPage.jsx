import { useState, useEffect, useRef } from 'react'
import { marketsApi } from '../../api/client'
import { TrendingUp, TrendingDown, RefreshCw } from 'lucide-react'
import QuickTradeModal from '../../components/QuickTradeModal'

export default function MarketsPage() {
  const [indices, setIndices] = useState([])
  const [loadingIndices, setLoadingIndices] = useState(true)
  
  const [selectedUnderlying, setSelectedUnderlying] = useState('BANKNIFTY')
  // For mock expiry we just use a hardcoded or today's date + some days, 
  // since the backend mock generates it anyway.
  const [expiry, setExpiry] = useState('')
  const [availableExpiries, setAvailableExpiries] = useState([]) 
  
  const [optionChain, setOptionChain] = useState([])
  const [loadingChain, setLoadingChain] = useState(true)
  
  const [selectedTrade, setSelectedTrade] = useState(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  
  const atmRowRef = useRef(null)
  const hasScrolledToATM = useRef(false)

  const handleManualRefresh = async () => {
    setIsRefreshing(true)
    await Promise.all([fetchIndices(), fetchOptionChain()])
    setTimeout(() => setIsRefreshing(false), 600)
  }

  const fetchIndices = async () => {
    try {
      const data = await marketsApi.indices()
      setIndices(data)
    } catch (err) {
      console.error('Error fetching indices', err)
    } finally {
      setLoadingIndices(false)
    }
  }

  const fetchOptionChain = async () => {
    if (!expiry) return;
    try {
      setLoadingChain(true)
      const data = await marketsApi.optionChain(selectedUnderlying, expiry)
      setOptionChain(data)
    } catch (err) {
      console.error('Error fetching option chain', err)
    } finally {
      setLoadingChain(false)
    }
  }

  // Polling for indices
  useEffect(() => {
    fetchIndices()
    const interval = setInterval(fetchIndices, 1000)
    return () => clearInterval(interval)
  }, [])

  // Refetch option chain when underlying or expiry changes, and poll
  // Fetch dynamic expiries when underlying changes
  useEffect(() => {
    const fetchExpiries = async () => {
      try {
        const data = await marketsApi.expiries(selectedUnderlying)
        if (data && data.length > 0) {
          setAvailableExpiries(data)
          setExpiry(data[0]) // Select first expiry by default
        } else {
          // Fallbacks if API fails
          setAvailableExpiries(['2026-07-28', '2026-08-25'])
          setExpiry('2026-07-28')
        }
      } catch (err) {
        console.error('Failed to fetch expiries', err)
        setAvailableExpiries(['2026-07-28', '2026-08-25'])
        setExpiry('2026-07-28')
      }
    }
    fetchExpiries()
    hasScrolledToATM.current = false // Reset scroll on underlying change
  }, [selectedUnderlying])

  useEffect(() => {
    hasScrolledToATM.current = false // Reset scroll on expiry change
  }, [expiry])

  useEffect(() => {
    fetchOptionChain()
    const interval = setInterval(fetchOptionChain, 1000)
    return () => clearInterval(interval)
  }, [selectedUnderlying, expiry])

  const spotPrice = indices.find(idx => idx.symbol === selectedUnderlying)?.ltp || 0
  
  let atmStrike = 0
  if (spotPrice && optionChain.length > 0) {
    atmStrike = optionChain.reduce((prev, curr) => {
      return (Math.abs(curr.strike_price - spotPrice) < Math.abs(prev.strike_price - spotPrice) ? curr : prev)
    }).strike_price
  }

  // Scroll to ATM row on load
  useEffect(() => {
    if (!loadingChain && atmRowRef.current && !hasScrolledToATM.current) {
      atmRowRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
      hasScrolledToATM.current = true
    }
  }, [loadingChain, optionChain])

  return (
    <div className="page pb-20">
      <div className="markets-header-bar">
        <h2>Live Markets</h2>
        <button 
          className={`btn-refresh-icon ${isRefreshing ? 'spinning' : ''}`} 
          onClick={handleManualRefresh}
          title="Refresh Market Data"
        >
          <RefreshCw size={18} />
        </button>
      </div>

      {/* Indices Watchlist Carousel */}
      <div className="stats-grid" style={{ marginBottom: '24px' }}>
        {loadingIndices && indices.length === 0 ? (
          <p>Loading market data...</p>
        ) : (
          indices.map((idx) => (
            <div 
              key={idx.symbol} 
              className={`stat-card ${selectedUnderlying === idx.symbol ? 'selected-idx' : ''}`}
              onClick={() => setSelectedUnderlying(idx.symbol)}
              style={{ 
                cursor: 'pointer', 
                border: selectedUnderlying === idx.symbol ? '2px solid var(--primary)' : '2px solid transparent'
              }}
            >
              <div className="stat-header">
                <h3>{idx.symbol}</h3>
              </div>
              <div className="stat-value" style={{ fontSize: '1.4rem' }}>
                {idx.ltp.toFixed(2)}
              </div>
              <div className={`stat-change ${idx.change >= 0 ? 'profit' : 'loss'}`}>
                {idx.change >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                <span>{idx.change} ({idx.change_percent}%)</span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Option Chain Section */}
      <div className="card markets-card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h3 style={{ margin: 0 }}>{selectedUnderlying} Option Chain</h3>
            {spotPrice > 0 && <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Spot: <span style={{ color: 'var(--text)', fontWeight: 600 }}>{spotPrice.toFixed(2)}</span></span>}
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Expiry:</span>
            <select 
              className="form-control" 
              value={expiry} 
              onChange={(e) => setExpiry(e.target.value)}
              style={{ padding: '4px 8px', width: 'auto', minHeight: '32px' }}
            >
              {availableExpiries.map(exp => (
                <option key={exp} value={exp}>{new Date(exp).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="card-body" style={{ padding: '0' }}>
          {loadingChain && optionChain.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center' }}><div className="spinner" /></div>
          ) : (
            <div className="oc-container" style={{ maxHeight: '65vh', overflowY: 'auto' }}>
              <table className="oc-table">
                <thead style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--bg-card)' }}>
                  <tr>
                    <th colSpan="3" className="center" style={{ borderRight: '1px solid var(--border)' }}>CALLS</th>
                    <th className="center">STRIKE</th>
                    <th colSpan="3" className="center" style={{ borderLeft: '1px solid var(--border)' }}>PUTS</th>
                  </tr>
                  <tr>
                    <th className="center">OI</th>
                    <th className="center">Vol</th>
                    <th className="center" style={{ borderRight: '1px solid var(--border)' }}>LTP</th>
                    <th className="center" style={{ backgroundColor: 'var(--bg)' }}>Price</th>
                    <th className="center" style={{ borderLeft: '1px solid var(--border)' }}>LTP</th>
                    <th className="center">Vol</th>
                    <th className="center">OI</th>
                  </tr>
                </thead>
                <tbody>
                  {optionChain.map((row) => {
                    const isCallITM = spotPrice > 0 && row.strike_price < spotPrice;
                    const isPutITM = spotPrice > 0 && row.strike_price > spotPrice;
                    const isATM = row.strike_price === atmStrike;

                    return (
                      <tr 
                        key={row.strike_price} 
                        className={isATM ? 'oc-atm-row' : ''}
                        ref={isATM ? atmRowRef : null}
                      >
                        {/* Calls */}
                        <td className={`center ${isCallITM ? 'oc-itm' : ''}`} style={{ color: 'var(--text-muted)' }}>{row.call_options.market_data.oi}</td>
                        <td className={`center ${isCallITM ? 'oc-itm' : ''}`} style={{ color: 'var(--text-muted)' }}>{row.call_options.market_data.volume}</td>
                        <td className={`center ${isCallITM ? 'oc-itm' : ''}`} style={{ borderRight: '1px solid var(--border)' }}>
                          <span 
                            className="oc-ltp"
                            onClick={() => setSelectedTrade({ strike: row.strike_price, type: 'CE', ltp: row.call_options.market_data.ltp, symbol: selectedUnderlying, expiry, instrument_key: row.call_options.instrument_key })}
                          >
                            {row.call_options.market_data.ltp.toFixed(2)}
                          </span>
                        </td>
                        
                        {/* Strike */}
                        <td className={`center oc-strike ${isATM ? 'atm-strike' : ''}`}>
                          {row.strike_price}
                        </td>
                        
                        {/* Puts */}
                        <td className={`center ${isPutITM ? 'oc-itm' : ''}`} style={{ borderLeft: '1px solid var(--border)' }}>
                          <span 
                            className="oc-ltp"
                            onClick={() => setSelectedTrade({ strike: row.strike_price, type: 'PE', ltp: row.put_options.market_data.ltp, symbol: selectedUnderlying, expiry, instrument_key: row.put_options.instrument_key })}
                          >
                            {row.put_options.market_data.ltp.toFixed(2)}
                          </span>
                        </td>
                        <td className={`center ${isPutITM ? 'oc-itm' : ''}`} style={{ color: 'var(--text-muted)' }}>{row.put_options.market_data.volume}</td>
                        <td className={`center ${isPutITM ? 'oc-itm' : ''}`} style={{ color: 'var(--text-muted)' }}>{row.put_options.market_data.oi}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <QuickTradeModal 
        tradeDetails={selectedTrade} 
        onClose={() => setSelectedTrade(null)} 
        onExecute={() => {
          // Could show a success toast here
        }}
      />
    </div>
  )
}
