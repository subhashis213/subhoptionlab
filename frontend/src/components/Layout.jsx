import { Outlet } from 'react-router-dom'
import { useState, useEffect } from 'react'
import BottomNav from './BottomNav'
import { Sun, Moon } from 'lucide-react'

export default function Layout() {
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark')
  }

  return (
    <div className="app-layout">
      <button 
        onClick={toggleTheme} 
        style={{
          position: 'fixed',
          top: '16px',
          right: '16px',
          zIndex: 1000,
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: '50%',
          width: '40px',
          height: '40px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text)',
          cursor: 'pointer',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
        }}
      >
        {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
      </button>
      <main className="main-content">
        <Outlet />
      </main>
      <BottomNav />
    </div>
  )
}
