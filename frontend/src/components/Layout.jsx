import { Outlet } from 'react-router-dom'
import { useState, useEffect } from 'react'
import BottomNav from './BottomNav'
import { Sun, Moon } from 'lucide-react'

export default function Layout() {
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') || 'dark'
    document.documentElement.setAttribute('data-theme', savedTheme)
  }, [])

  return (
    <div className="app-layout">
      <main className="main-content">
        <Outlet />
      </main>
      <BottomNav />
    </div>
  )
}
