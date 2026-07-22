import React, { useState } from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'
import CalendarAnalytics from './CalendarAnalytics'

export default function ResultsDashboard({ results }) {
  const [activeTab, setActiveTab] = useState('overview')
  const [expandedDay, setExpandedDay] = useState(null)
  const { metrics, daily_results, strategy, date_from, date_to } = results

  if (!metrics || !daily_results) {
    return (
      <div className="empty-state">
        <p>No results available. Run a backtest first.</p>
      </div>
    )
  }

  const isProfit = metrics.overall_profit >= 0

  // Helper for formatting currency/points with Indian number system commas
  const fmt = (val, decimals = 2) => {
    if (val === null || val === undefined) return '0.00'
    const num = Number(val)
    if (isNaN(num)) return '0.00'
    return num.toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  }

  return (
    <div className="results-dashboard">
      {/* Top Banner / Summary */}
      <div className="results-header">
        <div className="summary-main">
          <span className="summary-label">Total Backtest P&L</span>
          <h2 className={isProfit ? 'profit-text' : 'loss-text'}>
            {isProfit ? '+' : ''}₹{fmt(metrics.overall_profit)}
            <span className="points-sub">({isProfit ? '+' : ''}{fmt(metrics.overall_profit_points)} pts)</span>
          </h2>
        </div>

        <div className="summary-details">
          <div className="detail-item">
            <span className="label">🏷️ Symbol</span>
            <span className="value badge">{strategy.symbol}</span>
          </div>
          <div className="detail-item">
            <span className="label">📅 Period</span>
            <span className="value">{date_from} → {date_to} ({metrics.total_trading_days} days)</span>
          </div>
          <div className="detail-item">
            <span className="label">🎯 Win Rate</span>
            <span className="value win-highlight">{fmt(metrics.win_pct, 1)}% <small>({metrics.win_days}W / {metrics.loss_days}L)</small></span>
          </div>
          <div className="detail-item">
            <span className="label">📉 Max Drawdown</span>
            <span className="value loss-text">-₹{fmt(metrics.max_drawdown)} <small>({fmt(metrics.max_drawdown_pct, 1)}%)</small></span>
          </div>
        </div>
      </div>

      {/* Navigation Sub-tabs */}
      <div className="results-tabs">
        <button
          className={`sub-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <span>📊</span> Overview & Metrics
        </button>
        <button
          className={`sub-tab ${activeTab === 'chart' ? 'active' : ''}`}
          onClick={() => setActiveTab('chart')}
        >
          <span>📈</span> Equity Curve
        </button>
        <button
          className={`sub-tab ${activeTab === 'daily' ? 'active' : ''}`}
          onClick={() => setActiveTab('daily')}
        >
          <span>📋</span> Daily Execution Logs <span className="tab-count">{daily_results.length}</span>
        </button>
        <button
          className={`sub-tab ${activeTab === 'calendar' ? 'active' : ''}`}
          onClick={() => setActiveTab('calendar')}
        >
          <span>📅</span> Calendar Analytics
        </button>
      </div>

      {/* Tab 1: Overview & Metrics Grid */}
      {activeTab === 'overview' && (
        <div className="overview-grid">
          <div className="metric-card">
            <h3>Avg Day Profit</h3>
            <p className={metrics.avg_day_profit >= 0 ? 'profit-text' : 'loss-text'}>
              {metrics.avg_day_profit >= 0 ? '+' : ''}₹{fmt(metrics.avg_day_profit)}
            </p>
          </div>

          <div className="metric-card profit-card">
            <h3>Max Single Day Profit</h3>
            <p className="profit-text">+₹{fmt(metrics.max_profit)}</p>
          </div>

          <div className="metric-card loss-card">
            <h3>Max Single Day Loss</h3>
            <p className="loss-text">-₹{fmt(Math.abs(metrics.max_loss))}</p>
          </div>

          <div className="metric-card">
            <h3>Expectancy (Per Trade)</h3>
            <p className={metrics.expectancy >= 0 ? 'profit-text' : 'loss-text'}>
              {metrics.expectancy >= 0 ? '+' : ''}₹{fmt(metrics.expectancy)}
            </p>
          </div>

          <div className="metric-card profit-card">
            <h3>Avg Profit on Win Days</h3>
            <p className="profit-text">+₹{fmt(metrics.avg_profit_on_win_days)}</p>
          </div>

          <div className="metric-card loss-card">
            <h3>Avg Loss on Loss Days</h3>
            <p className="loss-text">-₹{fmt(Math.abs(metrics.avg_loss_on_loss_days))}</p>
          </div>

          <div className="metric-card">
            <h3>Win / Loss Streaks</h3>
            <p className="streak-value">
              <span className="profit-text">{metrics.max_win_streak} Max Wins</span>
              <span className="streak-sep">/</span>
              <span className="loss-text">{metrics.max_loss_streak} Max Losses</span>
            </p>
          </div>

          <div className="metric-card">
            <h3>Drawdown Recovery</h3>
            <p className="recovery-value">{metrics.recovery_days} days to recover</p>
          </div>

          {/* Exit breakdown */}
          <div className="metric-card span-2 exit-breakdown-card">
            <h3>Exit Reasons Breakdown</h3>
            <div className="exit-stats">
              <div className="exit-item">
                <span className="exit-dot sl-dot"></span>
                <span className="exit-label">Stop Loss Hit:</span>
                <strong className="loss-text">{metrics.sl_hit_count} days</strong>
              </div>
              <div className="exit-item">
                <span className="exit-dot tp-dot"></span>
                <span className="exit-label">Target Hit:</span>
                <strong className="profit-text">{metrics.tp_hit_count} days</strong>
              </div>
              <div className="exit-item">
                <span className="exit-dot time-dot"></span>
                <span className="exit-label">Time Exit (End of Day):</span>
                <strong>{metrics.time_exit_count} days</strong>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Equity Curve Chart */}
      {activeTab === 'chart' && (() => {
        const curve = metrics.equity_curve || []
        const peak = curve.length ? Math.max(...curve.map(d => d.cumulative)) : 0
        const low = curve.length ? Math.min(...curve.map(d => d.cumulative)) : 0
        const finalPnl = curve.length ? curve[curve.length - 1].cumulative : metrics.overall_profit

        const CustomTooltip = ({ active, payload, label }) => {
          if (active && payload && payload[0]) {
            const val = payload[0].value
            const isP = val >= 0
            return (
              <div className="custom-chart-tooltip">
                <div className="tooltip-header">📅 {label}</div>
                <div className="tooltip-body">
                  <span className="tooltip-label">Cumulative P&L:</span>
                  <strong className={isP ? 'profit-text' : 'loss-text'}>
                    {isP ? '+' : ''}₹{fmt(val)}
                  </strong>
                </div>
                <div className="tooltip-footer">
                  <span className={`tooltip-status ${isP ? 'status-profit' : 'status-loss'}`}>
                    {isP ? '🟢 Net Profitable' : '🔴 Net Drawdown'}
                  </span>
                </div>
              </div>
            )
          }
          return null
        }

        return (
          <div className="chart-container">
            <div className="chart-header-row">
              <div className="chart-title-box">
                <h3>Cumulative P&L Trajectory</h3>
                <p>Track your strategy's day-by-day compounding growth over {date_from} → {date_to}</p>
              </div>
              <div className="chart-pills">
                <div className="chart-pill">
                  <span>🚀 Peak Equity</span>
                  <strong className="profit-text">+₹{fmt(peak)}</strong>
                </div>
                <div className="chart-pill">
                  <span>💰 Final Net P&L</span>
                  <strong className={finalPnl >= 0 ? 'profit-text' : 'loss-text'}>
                    {finalPnl >= 0 ? '+' : ''}₹{fmt(finalPnl)}
                  </strong>
                </div>
                <div className="chart-pill">
                  <span>📉 Lowest Dip</span>
                  <strong className="loss-text">₹{fmt(low)}</strong>
                </div>
              </div>
            </div>

            <div className="recharts-wrapper modern-chart-box">
              <ResponsiveContainer width="100%" height={400}>
                <AreaChart data={curve} margin={{ top: 20, right: 30, left: 20, bottom: 10 }}>
                  <defs>
                    <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={isProfit ? '#10b981' : '#3b82f6'} stopOpacity={0.45}/>
                      <stop offset="95%" stopColor={isProfit ? '#10b981' : '#3b82f6'} stopOpacity={0.0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" opacity={0.6} />
                  <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={12} tickMargin={8} />
                  <YAxis stroke="var(--text-muted)" fontSize={12} tickFormatter={val => `₹${Number(val).toLocaleString('en-IN')}`} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="cumulative"
                    stroke={isProfit ? '#10b981' : '#3b82f6'}
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#colorPnl)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        )
      })()}

      {/* Tab 3: Daily Logs Table */}
      {activeTab === 'daily' && (
        <div className="table-container">
          <div className="table-toolbar">
            <span>Showing all <strong>{daily_results.length}</strong> trading days</span>
            <span className="table-tip">💡 Click on any row to expand Leg-by-Leg Execution Details</span>
          </div>
          <table className="daily-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Expiry</th>
                <th>Underlying</th>
                <th>ATM Strike</th>
                <th>Exit Reason</th>
                <th>Points P&L</th>
                <th>Total P&L (₹)</th>
              </tr>
            </thead>
            <tbody>
              {daily_results.map((day, i) => {
                const isDayProfit = day.total_pnl_value >= 0
                return (
                  <React.Fragment key={i}>
                    <tr
                      className={`daily-row ${isDayProfit ? 'row-profit-highlight' : 'row-loss-highlight'}`}
                      onClick={() => setExpandedDay(expandedDay === i ? null : i)}
                      title="Click to expand leg details"
                    >
                      <td className="td-date">
                        <span className="expand-arrow">{expandedDay === i ? '▾' : '▸'}</span>
                        <strong>{day.trade_date}</strong>
                      </td>
                      <td>{day.expiry_date}</td>
                      <td>₹{fmt(day.underlying_price, 1)}</td>
                      <td><span className="atm-badge">{day.atm_strike}</span></td>
                      <td>
                        <span className={`exit-badge ${day.exit_reason.toLowerCase().includes('sl') ? 'leg_sl_hit' : day.exit_reason.toLowerCase().includes('target') ? 'leg_target_hit' : 'time_exit'}`}>
                          {day.exit_reason.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className={day.total_pnl_points >= 0 ? 'profit-text' : 'loss-text'}>
                        {day.total_pnl_points >= 0 ? '+' : ''}{fmt(day.total_pnl_points)} pts
                      </td>
                      <td className={isDayProfit ? 'profit-text' : 'loss-text'}>
                        <span className="pnl-cell-amount">
                          {isDayProfit ? '+' : ''}₹{fmt(day.total_pnl_value)}
                        </span>
                      </td>
                    </tr>
                    {expandedDay === i && day.legs && (
                      <tr className="sub-row-expanded">
                        <td colSpan="7" className="sub-row-cell">
                          <div className="sub-table-card">
                            <div className="sub-table-header">
                              <span>⚡ Leg-by-Leg Execution Breakdown ({day.trade_date})</span>
                            </div>
                            <table className="inner-legs-table">
                              <thead>
                                <tr>
                                  <th>Option Leg</th>
                                  <th>Strike</th>
                                  <th className="text-right">Entry Price</th>
                                  <th className="text-right">Exit Price</th>
                                  <th className="text-right">Leg P&L (pts)</th>
                                  <th className="text-right">Leg P&L (₹)</th>
                                  <th className="text-center">Exit Reason</th>
                                </tr>
                              </thead>
                              <tbody>
                                {day.legs.map((leg, li) => {
                                  const isLegProfit = leg.pnl_value >= 0
                                  return (
                                    <tr key={li}>
                                      <td className="font-semibold">
                                        <span className={leg.option_type === 'CE' ? 'tag-ce' : 'tag-pe'}>
                                          {leg.option_type}
                                        </span>
                                        {' '}{leg.action}
                                      </td>
                                      <td>{leg.strike}</td>
                                      <td className="text-right">₹{fmt(leg.entry_price)}</td>
                                      <td className="text-right">₹{fmt(leg.exit_price)}</td>
                                      <td className={`text-right font-bold ${leg.pnl_points >= 0 ? 'profit-text' : 'loss-text'}`}>
                                        {leg.pnl_points >= 0 ? '+' : ''}{fmt(leg.pnl_points)}
                                      </td>
                                      <td className={`text-right font-bold ${isLegProfit ? 'profit-text' : 'loss-text'}`}>
                                        {isLegProfit ? '+' : ''}₹{fmt(leg.pnl_value)}
                                      </td>
                                      <td className="text-center">
                                        <span className={`exit-badge-sm ${leg.exit_reason.toLowerCase().includes('sl') ? 'sl-hit-sm' : 'time-hit-sm'}`}>
                                          {leg.exit_reason.replace(/_/g, ' ').toUpperCase()}
                                        </span>
                                      </td>
                                    </tr>
                                  )
                                })}
                              </tbody>
                            </table>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 4: Calendar Analytics */}
      {activeTab === 'calendar' && (
        <CalendarAnalytics daily_results={daily_results} fmt={fmt} />
      )}
    </div>
  )
}
