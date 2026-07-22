import React, { useState, useMemo } from 'react'

export default function CalendarAnalytics({ daily_results, fmt }) {
  // Extract unique years and months from daily_results
  const availableDates = useMemo(() => {
    const years = new Set()
    const monthsByYear = {}
    
    daily_results.forEach(day => {
      const d = new Date(day.trade_date)
      const year = d.getFullYear()
      const month = d.getMonth()
      
      years.add(year)
      if (!monthsByYear[year]) monthsByYear[year] = new Set()
      monthsByYear[year].add(month)
    })
    
    return {
      years: Array.from(years).sort((a, b) => b - a), // descending
      monthsByYear
    }
  }, [daily_results])

  const [selectedYear, setSelectedYear] = useState(availableDates.years[0] || new Date().getFullYear())
  
  // Default to the highest month in the selected year
  const availableMonths = availableDates.monthsByYear[selectedYear] ? Array.from(availableDates.monthsByYear[selectedYear]).sort((a, b) => b - a) : []
  const [selectedMonth, setSelectedMonth] = useState(availableMonths[0] ?? new Date().getMonth())

  // Handle Year Change
  const handleYearChange = (e) => {
    const newYear = parseInt(e.target.value)
    setSelectedYear(newYear)
    const newYearMonths = availableDates.monthsByYear[newYear] ? Array.from(availableDates.monthsByYear[newYear]).sort((a, b) => b - a) : []
    if (newYearMonths.length > 0) {
      setSelectedMonth(newYearMonths[0])
    }
  }

  // Filter daily_results for the selected year and month
  const currentMonthResults = useMemo(() => {
    return daily_results.filter(day => {
      const d = new Date(day.trade_date)
      return d.getFullYear() === selectedYear && d.getMonth() === selectedMonth
    })
  }, [daily_results, selectedYear, selectedMonth])

  // Build Calendar Grid Data
  const calendarGrid = useMemo(() => {
    const firstDay = new Date(selectedYear, selectedMonth, 1).getDay()
    const daysInMonth = new Date(selectedYear, selectedMonth + 1, 0).getDate()
    
    const grid = []
    let currentWeek = new Array(7).fill(null)
    
    for (let i = 0; i < firstDay; i++) {
      currentWeek[i] = null
    }
    
    for (let date = 1; date <= daysInMonth; date++) {
      const dayOfWeek = new Date(selectedYear, selectedMonth, date).getDay()
      
      // Format to YYYY-MM-DD to match trade_date
      const dateString = `${selectedYear}-${String(selectedMonth + 1).padStart(2, '0')}-${String(date).padStart(2, '0')}`
      
      const dayData = currentMonthResults.find(d => d.trade_date === dateString)
      
      currentWeek[dayOfWeek] = {
        date,
        data: dayData || null
      }
      
      if (dayOfWeek === 6 || date === daysInMonth) {
        grid.push(currentWeek)
        currentWeek = new Array(7).fill(null)
      }
    }
    
    return grid
  }, [selectedYear, selectedMonth, currentMonthResults])

  // Compute Weekday Performance (using all daily_results, not just selected month)
  const weekdayAnalytics = useMemo(() => {
    const stats = {
      1: { name: 'Monday', totalPnl: 0, wins: 0, losses: 0, maxProfit: 0, maxLoss: 0, count: 0 },
      2: { name: 'Tuesday', totalPnl: 0, wins: 0, losses: 0, maxProfit: 0, maxLoss: 0, count: 0 },
      3: { name: 'Wednesday', totalPnl: 0, wins: 0, losses: 0, maxProfit: 0, maxLoss: 0, count: 0 },
      4: { name: 'Thursday', totalPnl: 0, wins: 0, losses: 0, maxProfit: 0, maxLoss: 0, count: 0 },
      5: { name: 'Friday', totalPnl: 0, wins: 0, losses: 0, maxProfit: 0, maxLoss: 0, count: 0 },
    }

    daily_results.forEach(day => {
      const d = new Date(day.trade_date)
      const wDay = d.getDay() // 0 = Sun, 1 = Mon ... 6 = Sat
      if (stats[wDay]) {
        const pnl = day.total_pnl_value
        stats[wDay].count++
        stats[wDay].totalPnl += pnl
        
        if (pnl > 0) {
          stats[wDay].wins++
          stats[wDay].maxProfit = Math.max(stats[wDay].maxProfit, pnl)
        } else {
          stats[wDay].losses++
          stats[wDay].maxLoss = Math.min(stats[wDay].maxLoss, pnl)
        }
      }
    })

    return Object.values(stats)
  }, [daily_results])

  const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

  return (
    <div className="calendar-analytics-container">
      
      {/* Filters */}
      <div className="calendar-toolbar">
        <div className="calendar-filters">
          <select value={selectedYear} onChange={handleYearChange} className="calendar-select">
            {availableDates.years.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
          <select value={selectedMonth} onChange={(e) => setSelectedMonth(parseInt(e.target.value))} className="calendar-select">
            {availableMonths.map(m => <option key={m} value={m}>{monthNames[m]}</option>)}
          </select>
        </div>
        <div className="calendar-summary">
          {monthNames[selectedMonth]} {selectedYear} Performance
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="calendar-grid-wrapper modern-chart-box">
        <table className="calendar-grid">
          <thead>
            <tr>
              <th>Sun</th>
              <th>Mon</th>
              <th>Tue</th>
              <th>Wed</th>
              <th>Thu</th>
              <th>Fri</th>
              <th>Sat</th>
            </tr>
          </thead>
          <tbody>
            {calendarGrid.map((week, wIdx) => (
              <tr key={wIdx}>
                {week.map((day, dIdx) => {
                  if (!day) return <td key={dIdx} className="cal-cell empty"></td>
                  
                  const pnl = day.data ? day.data.total_pnl_value : null
                  const isProfit = pnl > 0
                  const isLoss = pnl < 0
                  const isNeutral = pnl === 0
                  
                  let cellClass = 'cal-cell'
                  if (isProfit) cellClass += ' cal-profit'
                  else if (isLoss) cellClass += ' cal-loss'
                  else if (day.data) cellClass += ' cal-neutral'
                  else cellClass += ' cal-no-trade'

                  return (
                    <td key={dIdx} className={cellClass}>
                      <div className="cal-date">{day.date}</div>
                      {day.data && (
                        <div className="cal-pnl">
                          {pnl > 0 ? '+' : ''}₹{fmt(pnl)}
                        </div>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Weekday Analytics Table */}
      <div className="weekday-analytics-wrapper modern-chart-box" style={{ marginTop: '24px' }}>
        <h3 style={{ marginBottom: '8px' }}>Day of the Week Analytics</h3>
        <p className="analytics-subtitle" style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '16px' }}>
          Aggregated performance across the entire backtest period
        </p>
        <div className="table-container">
          <table className="daily-table weekday-table">
            <thead>
              <tr>
                <th>Weekday</th>
                <th>Trades</th>
                <th>Win Rate</th>
                <th>Total P&L</th>
                <th>Max Profit</th>
                <th>Max Loss</th>
              </tr>
            </thead>
            <tbody>
              {weekdayAnalytics.map((w, i) => {
                const winRate = w.count > 0 ? (w.wins / w.count) * 100 : 0
                const isProfit = w.totalPnl >= 0
                
                return (
                  <tr key={i} className="daily-row">
                    <td><strong>{w.name}</strong></td>
                    <td>{w.count}</td>
                    <td>
                      <span className={winRate >= 50 ? 'profit-text' : 'loss-text'}>
                        {w.count > 0 ? `${winRate.toFixed(1)}%` : '-'}
                      </span>
                    </td>
                    <td className={isProfit ? 'profit-text' : 'loss-text'}>
                      <strong>{isProfit ? '+' : ''}₹{fmt(w.totalPnl)}</strong>
                    </td>
                    <td className="profit-text">{w.maxProfit > 0 ? `+₹${fmt(w.maxProfit)}` : '-'}</td>
                    <td className="loss-text">{w.maxLoss < 0 ? `-₹${fmt(Math.abs(w.maxLoss))}` : '-'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  )
}
