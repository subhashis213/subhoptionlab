/**
 * Admin Dashboard — overview stats.
 */
import { useState, useEffect } from 'react'
import { adminApi } from '../../api/client'
import { Users, BarChart3, Wallet, Activity } from 'lucide-react'

export default function AdminDashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const data = await adminApi.overview()
      setStats(data)
    } catch (err) {
      console.error(err)
    }
    setLoading(false)
  }

  if (loading) return <div className="page-loading"><div className="spinner" /></div>

  return (
    <div className="page admin-page">
      <div className="page-header">
        <h2>Admin Overview</h2>
      </div>

      {stats && (
        <div className="admin-stats-grid">
          <div className="admin-stat-card">
            <Users size={24} className="icon-users" />
            <span className="stat-label">Total Users</span>
            <span className="stat-value">{stats.total_users}</span>
          </div>
          
          <div className="admin-stat-card">
            <Activity size={24} className="icon-active" />
            <span className="stat-label">Active Users</span>
            <span className="stat-value">{stats.active_users}</span>
          </div>

          <div className="admin-stat-card">
            <Wallet size={24} className="icon-wallet" />
            <span className="stat-label">Chips in Circulation</span>
            <span className="stat-value">₹{stats.total_virtual_chips_in_circulation?.toLocaleString('en-IN')}</span>
          </div>

          <div className="admin-stat-card">
            <BarChart3 size={24} className="icon-strategies" />
            <span className="stat-label">Global Strategies</span>
            <span className="stat-value">{stats.total_strategies} ({stats.active_strategies} active)</span>
          </div>
        </div>
      )}
    </div>
  )
}
