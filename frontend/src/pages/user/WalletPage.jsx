/**
 * Wallet Page — wallet card, transaction history.
 * Users CANNOT add chips — view only.
 */
import { useState, useEffect } from 'react'
import { walletApi } from '../../api/client'
import { Wallet, TrendingUp, TrendingDown, ArrowUpCircle, ArrowDownCircle, Activity } from 'lucide-react'

export default function WalletPage() {
  const [wallet, setWallet] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [w, t] = await Promise.all([
        walletApi.get(),
        walletApi.transactions(),
      ])
      setWallet(w)
      setTransactions(t.transactions || [])
    } catch (err) {
      console.error(err)
    }
    setLoading(false)
  }

  if (loading) return <div className="page-loading"><div className="spinner" /></div>

  return (
    <div className="page">
      <div className="page-header">
        <h2>Wallet</h2>
      </div>

      {/* Wallet Card */}
      <div className="wallet-card-hero">
        <div className="wallet-card-bg" />
        <div className="wallet-card-content">
          <Wallet size={24} className="wallet-icon" />
          <span className="wallet-label">Virtual Chips Balance</span>
          <h1 className="wallet-amount">
            ₹{(wallet?.virtual_chips_balance || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </h1>
          <div className="wallet-meta">
            <div className={`wallet-pnl ${(wallet?.unrealized_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
              <Activity size={14} />
              <span>Unrealized: ₹{(wallet?.unrealized_pnl || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Wallet Stats */}
      <div className="wallet-stats">
        <div className="wallet-stat">
          <ArrowUpCircle size={18} className="stat-icon positive" />
          <div>
            <span className="stat-label">Total Added</span>
            <span className="stat-value">₹{(wallet?.total_added || 0).toLocaleString('en-IN')}</span>
          </div>
        </div>
        <div className="wallet-stat">
          <ArrowDownCircle size={18} className="stat-icon negative" />
          <div>
            <span className="stat-label">Total Removed</span>
            <span className="stat-value">₹{(wallet?.total_removed || 0).toLocaleString('en-IN')}</span>
          </div>
        </div>
      </div>

      {/* Transaction History */}
      <div className="section">
        <h3>Transaction History</h3>
        {transactions.length === 0 ? (
          <div className="empty-state">
            <p>No transactions yet</p>
            <p className="hint">Admin will add virtual chips to your wallet</p>
          </div>
        ) : (
          <div className="tx-list">
            {transactions.map((tx) => (
              <div key={tx._id} className="tx-item">
                <div className={`tx-icon ${tx.type}`}>
                  {tx.type === 'add' ? <ArrowUpCircle size={18} /> : <ArrowDownCircle size={18} />}
                </div>
                <div className="tx-info">
                  <span className="tx-type">{tx.type === 'add' ? 'Chips Added' : 'Chips Removed'}</span>
                  <span className="tx-reason">{tx.reason}</span>
                  <span className="tx-time">
                    {new Date(tx.timestamp).toLocaleString('en-IN', {
                      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
                    })}
                  </span>
                </div>
                <span className={`tx-amount ${tx.type}`}>
                  {tx.type === 'add' ? '+' : '-'}₹{tx.amount.toLocaleString('en-IN')}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
