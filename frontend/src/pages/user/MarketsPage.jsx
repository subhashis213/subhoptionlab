import { useState, useEffect, useRef, useMemo } from 'react'
import { marketsApi } from '../../api/client'
import { TrendingUp, TrendingDown, RefreshCw, Search } from 'lucide-react'
import QuickTradeModal from '../../components/QuickTradeModal'
import useMarketStream from '../../hooks/useMarketStream'

export default function MarketsPage() {
  const [indices, setIndices] = useState([])
  const [loadingIndices, setLoadingIndices] = useState(true)
  const [topStocks, setTopStocks] = useState({ gainers: [], losers: [] })
  const [loadingTopStocks, setLoadingTopStocks] = useState(true)
  
  const [selectedUnderlying, setSelectedUnderlying] = useState('BANKNIFTY')
  const [isStock, setIsStock] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)

  const [expiry, setExpiry] = useState('')
  const [availableExpiries, setAvailableExpiries] = useState([]) 
  
  const [optionChain, setOptionChain] = useState([])
  const [loadingChain, setLoadingChain] = useState(true)
  
  const [selectedTrade, setSelectedTrade] = useState(null)
  
  const atmRowRef = useRef(null)
  const hasScrolledToATM = useRef(false)

  // Determine what keys to subscribe to via WebSockets
  const wsKeys = useMemo(() => {
    let keys = []
    if (indices.length > 0) {
      indices.forEach(idx => {
        const keyMap = { "NIFTY": "NSE_INDEX|Nifty 50", "BANKNIFTY": "NSE_INDEX|Nifty Bank", "FINNIFTY": "NSE_INDEX|Nifty Fin Service", "MIDCAPNIFTY": "NSE_INDEX|NIFTY MID SELECT" }
        keys.push(keyMap[idx.symbol] || `NSE_INDEX|${idx.symbol}`)
      })
    }
    if (isStock) {
      keys.push(`NSE_EQ|${selectedUnderlying}`)
    }
    
    // Add option chain keys
    if (optionChain.length > 0) {
      optionChain.forEach(row => {
        if (row.call_options?.instrument_key) keys.push(row.call_options.instrument_key.replace(':', '|'))
        if (row.put_options?.instrument_key) keys.push(row.put_options.instrument_key.replace(':', '|'))
      })
    }
    
    // Add top stock keys
    if (topStocks.gainers.length > 0) {
      topStocks.gainers.forEach(s => keys.push(s.instrument_key))
      topStocks.losers.forEach(s => keys.push(s.instrument_key))
    }
    
    return keys;
  }, [indices, optionChain, isStock, selectedUnderlying, topStocks])

  const liveData = useMarketStream(wsKeys)

  const fetchIndices = async () => {
    try {
      setLoadingIndices(true)
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

  const handleSearch = async (e) => {
    const q = e.target.value
    setSearchQuery(q)
    if (q.length > 1) {
      setIsSearching(true)
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/pt/markets/stocks/search?q=${q}`)
        if (res.ok) {
          const data = await res.json()
          setSearchResults(data)
        }
      } catch (err) {
        console.error(err)
      }
    } else {
      setSearchResults([])
      setIsSearching(false)
    }
  }

  const selectStock = (stockSymbol) => {
    setIsStock(true)
    setSelectedUnderlying(stockSymbol)
    setSearchQuery('')
    setSearchResults([])
    setIsSearching(false)
  }

  const fetchTopStocks = async () => {
    try {
      setLoadingTopStocks(true)
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/pt/markets/top-stocks`)
      if (res.ok) {
        const data = await res.json()
        setTopStocks(data)
      }
    } catch (err) {
      console.error('Error fetching top stocks', err)
    } finally {
      setLoadingTopStocks(false)
    }
  }

  useEffect(() => {
    fetchIndices()
    fetchTopStocks()
  }, [])

  useEffect(() => {
    const fetchExpiries = async () => {
      try {
        const data = await marketsApi.expiries(selectedUnderlying)
        if (data && data.length > 0) {
          setAvailableExpiries(data)
          setExpiry(data[0]) 
        } else {
          setAvailableExpiries(['2026-07-28', '2026-08-25'])
          setExpiry('2026-07-28')
        }
      } catch (err) {
        console.error('Failed to fetch expiries', err)
      }
    }
    fetchExpiries()
    hasScrolledToATM.current = false 
  }, [selectedUnderlying])

  useEffect(() => {
    hasScrolledToATM.current = false 
  }, [expiry])

  useEffect(() => {
    fetchOptionChain()
  }, [selectedUnderlying, expiry])

  // Process live spot price for selected underlying - new flat format: msg.ltp or msg.last_price
  let spotPrice = 0;
  if (!isStock) {
    const keyMap = { "NIFTY": "NSE_INDEX|Nifty 50", "BANKNIFTY": "NSE_INDEX|Nifty Bank", "FINNIFTY": "NSE_INDEX|Nifty Fin Service", "MIDCAPNIFTY": "NSE_INDEX|NIFTY MID SELECT" }
    const idx = indices.find(i => i.symbol === selectedUnderlying)
    const key = keyMap[selectedUnderlying]
    // New format: flat { ltp, last_price, ... }. Old fallback: ff.indexFF.ltpc.ltp
    spotPrice = liveData[key]?.ltp || liveData[key]?.last_price || liveData[key]?.ff?.indexFF?.ltpc?.ltp || idx?.ltp || 0
  } else {
    const key = `NSE_EQ|${selectedUnderlying}`
    spotPrice = liveData[key]?.ltp || liveData[key]?.last_price || liveData[key]?.ff?.marketFF?.ltpc?.ltp || 0
    if (spotPrice === 0) {
      const fallbackStock = topStocks.gainers.find(s => s.symbol === selectedUnderlying) || topStocks.losers.find(s => s.symbol === selectedUnderlying)
      if (fallbackStock) spotPrice = fallbackStock.ltp
    }
  }
  
  let atmStrike = 0
  if (spotPrice && optionChain.length > 0) {
    atmStrike = optionChain.reduce((prev, curr) => {
      return (Math.abs(curr.strike_price - spotPrice) < Math.abs(prev.strike_price - spotPrice) ? curr : prev)
    }).strike_price
  }

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
        <div style={{display: 'flex', gap: '8px', alignItems: 'center'}}>
           {/* F&O Search */}
           <div style={{ position: 'relative' }}>
             <div className="form-control" style={{display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 8px'}}>
               <Search size={16} color="var(--text-muted)" />
               <input 
                 type="text" 
                 placeholder="Search F&O Stocks..." 
                 value={searchQuery}
                 onChange={handleSearch}
                 style={{ border: 'none', background: 'transparent', color: 'var(--text)', outline: 'none', width: '150px' }}
               />
             </div>
             {searchResults.length > 0 && (
               <div style={{ position: 'absolute', top: '100%', right: 0, width: '250px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '8px', zIndex: 50, marginTop: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.2)' }}>
                 {searchResults.map(stock => (
                   <div 
                     key={stock.symbol}
                     onClick={() => selectStock(stock.symbol)}
                     style={{ padding: '12px', borderBottom: '1px solid var(--border)', cursor: 'pointer', display: 'flex', justifyContent: 'space-between' }}
                   >
                     <span style={{ fontWeight: 600 }}>{stock.symbol}</span>
                     <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Lot: {stock.lot_size}</span>
                   </div>
                 ))}
               </div>
             )}
           </div>
        </div>
      </div>

      {/* Indices Watchlist Carousel */}
      <div className="stats-grid" style={{ marginBottom: '24px' }}>
        {loadingIndices && indices.length === 0 ? (
          <p>Loading market data...</p>
        ) : (
          indices.map((idx) => {
            const keyMap = { "NIFTY": "NSE_INDEX|Nifty 50", "BANKNIFTY": "NSE_INDEX|Nifty Bank", "FINNIFTY": "NSE_INDEX|Nifty Fin Service", "MIDCAPNIFTY": "NSE_INDEX|NIFTY MID SELECT" }
            const liveInfo = liveData[keyMap[idx.symbol]]
            // New flat format: liveInfo.ltp — old fallbacks supported too
            const currentLtp = liveInfo?.ltp || liveInfo?.last_price || liveInfo?.ff?.indexFF?.ltpc?.ltp || idx.ltp
            const liveChange = liveInfo?.net_change ?? idx.change
            const liveChangePct = liveInfo?.change_percent ?? idx.change_percent
            
            return (
            <div 
              key={idx.symbol} 
              className={`stat-card ${!isStock && selectedUnderlying === idx.symbol ? 'selected-idx' : ''}`}
              onClick={() => { setIsStock(false); setSelectedUnderlying(idx.symbol) }}
              style={{ 
                cursor: 'pointer', 
                border: !isStock && selectedUnderlying === idx.symbol ? '2px solid var(--primary)' : '2px solid transparent'
              }}
            >
              <div className="stat-header">
                <h3>{idx.symbol}</h3>
              </div>
              <div className="stat-value" style={{ fontSize: '1.4rem' }}>
                {Number(currentLtp || 0).toFixed(2)}
              </div>
              <div className={`stat-change ${liveChange >= 0 ? 'profit' : 'loss'}`}>
                {liveChange >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                <span>{liveChange > 0 ? '+' : ''}{Number(liveChange || 0).toFixed(2)} ({Number(liveChangePct || 0).toFixed(2)}%)</span>
              </div>
            </div>
          )})
        )}
      </div>

      {/* Top Gainers & Losers */}
      <div style={{ display: 'flex', gap: '24px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: '300px' }}>
          <h3 style={{ marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp size={20} color="var(--success)" /> Top Gainers
          </h3>
          <div style={{ display: 'flex', gap: '12px', overflowX: 'auto', paddingBottom: '8px' }}>
            {loadingTopStocks ? <p>Loading...</p> : topStocks.gainers.map(s => {
              const liveInfo = liveData[s.instrument_key]
              const currentLtp = liveInfo?.ltp || liveInfo?.last_price || s.ltp
              const currentChangePct = liveInfo?.change_percent ?? s.change_percent
              return (
                <div key={s.symbol} className="stat-card" style={{ minWidth: '150px', cursor: 'pointer' }} onClick={() => selectStock(s.symbol)}>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{s.symbol}</div>
                  <div style={{ fontSize: '1.2rem', margin: '4px 0' }}>₹{Number(currentLtp).toFixed(2)}</div>
                  <div className="profit" style={{ fontSize: '0.8rem' }}>+{Number(currentChangePct).toFixed(2)}%</div>
                </div>
              )
            })}
          </div>
        </div>
        <div style={{ flex: 1, minWidth: '300px' }}>
          <h3 style={{ marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingDown size={20} color="var(--danger)" /> Top Losers
          </h3>
          <div style={{ display: 'flex', gap: '12px', overflowX: 'auto', paddingBottom: '8px' }}>
            {loadingTopStocks ? <p>Loading...</p> : topStocks.losers.map(s => {
              const liveInfo = liveData[s.instrument_key]
              const currentLtp = liveInfo?.ltp || liveInfo?.last_price || s.ltp
              const currentChangePct = liveInfo?.change_percent ?? s.change_percent
              return (
                <div key={s.symbol} className="stat-card" style={{ minWidth: '150px', cursor: 'pointer' }} onClick={() => selectStock(s.symbol)}>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{s.symbol}</div>
                  <div style={{ fontSize: '1.2rem', margin: '4px 0' }}>₹{Number(currentLtp).toFixed(2)}</div>
                  <div className="loss" style={{ fontSize: '0.8rem' }}>{Number(currentChangePct).toFixed(2)}%</div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Cash Market Section */}
      {isStock && (
        <div className="card markets-card" style={{ marginBottom: '24px' }}>
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                {selectedUnderlying} <span style={{ fontSize: '0.8rem', color: 'var(--primary)', background: 'var(--primary-light)', padding: '2px 8px', borderRadius: '4px' }}>EQUITY</span>
              </h3>
            </div>
            {spotPrice > 0 ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '24px', flexWrap: 'wrap' }}>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '1.8rem', fontWeight: 'bold' }}>₹{Number(spotPrice || 0).toFixed(2)}</div>
                </div>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <button 
                    className="btn-primary" 
                    style={{ padding: '10px 24px', background: 'var(--success)', borderColor: 'var(--success)', fontSize: '1rem', fontWeight: 600 }}
                    onClick={() => {
                       setSelectedTrade({ strike: 0, type: 'EQ', ltp: spotPrice, symbol: selectedUnderlying, expiry: '', instrument_key: `NSE_EQ|${selectedUnderlying}`, initialAction: 'BUY' })
                    }}
                  >
                    BUY STOCK
                  </button>
                  <button 
                    className="btn-primary" 
                    style={{ padding: '10px 24px', background: 'var(--danger)', borderColor: 'var(--danger)', fontSize: '1rem', fontWeight: 600 }}
                    onClick={() => {
                       setSelectedTrade({ strike: 0, type: 'EQ', ltp: spotPrice, symbol: selectedUnderlying, expiry: '', instrument_key: `NSE_EQ|${selectedUnderlying}`, initialAction: 'SELL' })
                    }}
                  >
                    SELL STOCK
                  </button>
                </div>
              </div>
            ) : (
               <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Waiting for live quote...</span>
            )}
          </div>
        </div>
      )}

      {/* Option Chain Section */}
      <div className="card markets-card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0 }}>{selectedUnderlying} {isStock ? 'Stock Option Chain' : 'Option Chain'}</h3>
            {spotPrice > 0 && <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Live Spot: <span style={{ color: 'var(--text)', fontWeight: 600 }}>{Number(spotPrice || 0).toFixed(2)}</span></span>}
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
                    
                    const rawCeKey = row.call_options?.instrument_key || '';
                    const rawPeKey = row.put_options?.instrument_key || '';
                    const ceKey = rawCeKey.replace(':', '|');
                    const peKey = rawPeKey.replace(':', '|');
                    
                    // New flat format: liveData[key].ltp — with old fallbacks
                    const ceLive = ceKey ? liveData[ceKey] : null
                    const peLive = peKey ? liveData[peKey] : null
                    const ceLtp = ceLive ? (ceLive.ltp || ceLive.last_price || ceLive.ff?.marketFF?.ltpc?.ltp) : row.call_options?.market_data?.ltp
                    const peLtp = peLive ? (peLive.ltp || peLive.last_price || peLive.ff?.marketFF?.ltpc?.ltp) : row.put_options?.market_data?.ltp

                    return (
                      <tr 
                        key={row.strike_price} 
                        className={isATM ? 'oc-atm-row' : ''}
                        ref={isATM ? atmRowRef : null}
                      >
                        {/* Calls */}
                        <td className={`center ${isCallITM ? 'oc-itm' : ''}`} style={{ color: 'var(--text-muted)' }}>{row.call_options?.market_data?.oi || 0}</td>
                        <td className={`center ${isCallITM ? 'oc-itm' : ''}`} style={{ color: 'var(--text-muted)' }}>{row.call_options?.market_data?.volume || 0}</td>
                        <td className={`center ${isCallITM ? 'oc-itm' : ''}`} style={{ borderRight: '1px solid var(--border)' }}>
                          {ceLtp != null ? (
                            <span 
                              className="oc-ltp"
                              onClick={() => setSelectedTrade({ strike: row.strike_price, type: 'CE', ltp: Number(ceLtp), symbol: selectedUnderlying, expiry, instrument_key: ceKey })}
                            >
                              {Number(ceLtp).toFixed(2)}
                            </span>
                          ) : '-'}
                        </td>
                        
                        {/* Strike */}
                        <td className={`center oc-strike ${isATM ? 'atm-strike' : ''}`}>
                          {row.strike_price}
                        </td>
                        
                        {/* Puts */}
                        <td className={`center ${isPutITM ? 'oc-itm' : ''}`} style={{ borderLeft: '1px solid var(--border)' }}>
                          {peLtp != null ? (
                            <span 
                              className="oc-ltp"
                              onClick={() => setSelectedTrade({ strike: row.strike_price, type: 'PE', ltp: Number(peLtp), symbol: selectedUnderlying, expiry, instrument_key: peKey })}
                            >
                              {Number(peLtp).toFixed(2)}
                            </span>
                          ) : '-'}
                        </td>
                        <td className={`center ${isPutITM ? 'oc-itm' : ''}`} style={{ color: 'var(--text-muted)' }}>{row.put_options?.market_data?.volume || 0}</td>
                        <td className={`center ${isPutITM ? 'oc-itm' : ''}`} style={{ color: 'var(--text-muted)' }}>{row.put_options?.market_data?.oi || 0}</td>
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
          // Toast happens inside modal
        }}
      />
    </div>
  )
}
