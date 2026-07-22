/**
 * Admin Users List & Chip Management
 */
import { useState, useEffect } from 'react'
import { adminApi } from '../../api/client'
import BottomSheet from '../../components/BottomSheet'
import { User, Shield, Search, ArrowUpCircle, ArrowDownCircle, Edit3 } from 'lucide-react'

export default function AdminUsers() {
  const [users, setUsers] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  
  // Bottom sheet state
  const [selectedUser, setSelectedUser] = useState(null)
  const [chipAction, setChipAction] = useState('add') // add or remove
  const [chipAmount, setChipAmount] = useState('')
  const [chipReason, setChipReason] = useState('')
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => {
      loadUsers()
    }, 500)
    return () => clearTimeout(timer)
  }, [search])

  const loadUsers = async () => {
    setLoading(true)
    try {
      const data = await adminApi.users({ search })
      setUsers(data.users || [])
    } catch (err) {
      console.error(err)
    }
    setLoading(false)
  }

  const openChipModal = (user, action) => {
    setSelectedUser(user)
    setChipAction(action)
    setChipAmount('')
    setChipReason('')
  }

  const handleChipSubmit = async () => {
    if (!chipAmount || Number(chipAmount) <= 0) return
    if (!chipReason) return
    
    setActionLoading(true)
    try {
      if (chipAction === 'add') {
        await adminApi.addChips(selectedUser._id, {
          amount: Number(chipAmount),
          reason: chipReason,
        })
      } else {
        await adminApi.removeChips(selectedUser._id, {
          amount: Number(chipAmount),
          reason: chipReason,
        })
      }
      setSelectedUser(null)
      loadUsers()
    } catch (err) {
      alert(err.message)
    }
    setActionLoading(false)
  }

  const toggleStatus = async (user) => {
    if (!confirm(`Change status of ${user.name} to ${user.status === 'active' ? 'blocked' : 'active'}?`)) return
    try {
      await adminApi.updateStatus(user._id, user.status === 'active' ? 'blocked' : 'active')
      loadUsers()
    } catch (err) {
      alert(err.message)
    }
  }

  return (
    <div className="page admin-page">
      <div className="page-header">
        <h2>User Management</h2>
      </div>

      <div className="search-bar">
        <Search size={18} />
        <input 
          type="text" 
          placeholder="Search by name, email, phone..." 
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="page-loading"><div className="spinner" /></div>
      ) : (
        <div className="admin-user-list">
          {users.map((u) => (
            <div key={u._id} className="admin-user-card">
              <div className="user-card-header">
                <div className="user-info-basic">
                  <User size={18} />
                  <strong>{u.name}</strong>
                  {u.role === 'admin' && <Shield size={14} className="text-primary" />}
                </div>
                <button 
                  className={`status-toggle ${u.status}`}
                  onClick={() => toggleStatus(u)}
                  disabled={u.role === 'admin'}
                >
                  {u.status}
                </button>
              </div>
              
              <div className="user-card-body">
                <span>{u.email}</span>
                <span>{u.phone || 'No phone'}</span>
                <span className="wallet-balance">
                  Chips: ₹{u.wallet_balance?.toLocaleString('en-IN') || 0}
                </span>
              </div>

              {u.role !== 'admin' && (
                <div className="user-card-actions">
                  <button onClick={() => openChipModal(u, 'add')} className="btn-add">
                    <ArrowUpCircle size={16} /> Add Chips
                  </button>
                  <button onClick={() => openChipModal(u, 'remove')} className="btn-remove">
                    <ArrowDownCircle size={16} /> Remove Chips
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Chip Modal */}
      <BottomSheet 
        isOpen={!!selectedUser} 
        onClose={() => !actionLoading && setSelectedUser(null)}
        title={`${chipAction === 'add' ? 'Add Chips to' : 'Remove Chips from'} ${selectedUser?.name}`}
      >
        <div className="chip-form">
          <div className="form-group">
            <label>Amount (₹)</label>
            <input 
              type="number" 
              placeholder="e.g. 100000" 
              value={chipAmount}
              onChange={(e) => setChipAmount(e.target.value)}
              min="1"
            />
          </div>
          <div className="form-group">
            <label>Reason</label>
            <input 
              type="text" 
              placeholder="e.g. Initial capital, Reward, Penalty..." 
              value={chipReason}
              onChange={(e) => setChipReason(e.target.value)}
            />
          </div>
          <button 
            className="btn-primary btn-full" 
            onClick={handleChipSubmit}
            disabled={actionLoading || !chipAmount || !chipReason}
          >
            {actionLoading ? 'Processing...' : 'Confirm Transaction'}
          </button>
        </div>
      </BottomSheet>
    </div>
  )
}
