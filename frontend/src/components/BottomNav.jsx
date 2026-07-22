/**
 * Mobile bottom navigation bar.
 * Different tabs for User vs Admin roles.
 */
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Home, BarChart3, Wallet, History, User,
  Users, LayoutDashboard, Globe
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const userTabs = [
  { path: '/home', icon: Home, label: 'Home' },
  { path: '/markets', icon: Globe, label: 'Markets' },
  { path: '/strategies', icon: BarChart3, label: 'Strategies' },
  { path: '/wallet', icon: Wallet, label: 'Wallet' },
  { path: '/profile', icon: User, label: 'Profile' },
]

const adminTabs = [
  { path: '/admin', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/admin/users', icon: Users, label: 'Users' },
  { path: '/admin/global', icon: Globe, label: 'Global' },
  { path: '/admin/profile', icon: User, label: 'Profile' },
]

export default function BottomNav() {
  const { isAdmin } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const tabs = isAdmin ? adminTabs : userTabs

  return (
    <nav className="bottom-nav">
      {tabs.map((tab) => {
        const Icon = tab.icon
        const isActive = location.pathname === tab.path ||
          (tab.path !== '/' && location.pathname.startsWith(tab.path))

        return (
          <button
            key={tab.path}
            className={`bottom-nav-item ${isActive ? 'active' : ''}`}
            onClick={() => navigate(tab.path)}
          >
            <Icon size={22} strokeWidth={isActive ? 2.5 : 1.8} />
            <span>{tab.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
