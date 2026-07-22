/**
 * Auth context — manages authentication state across the app.
 */
import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authApi, setAuth, clearAuth, getToken, getUser, connectWebSocket } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getUser())
  const [token, setToken] = useState(() => getToken())
  const [loading, setLoading] = useState(true)
  const [wsConnection, setWsConnection] = useState(null)

  // Verify token on mount
  useEffect(() => {
    const verify = async () => {
      if (!token) {
        setLoading(false)
        return
      }
      try {
        const userData = await authApi.me()
        setUser(userData)
        setAuth(token, userData)
      } catch {
        clearAuth()
        setUser(null)
        setToken(null)
      }
      setLoading(false)
    }
    verify()
  }, [])

  // WebSocket connection
  useEffect(() => {
    if (token && user) {
      const conn = connectWebSocket(token, (message) => {
        // Dispatch custom event for components to listen
        window.dispatchEvent(new CustomEvent('pt-ws-message', { detail: message }))
      })
      setWsConnection(conn)
      return () => conn.close()
    }
  }, [token, user?._id])

  const login = useCallback(async (email, password) => {
    const result = await authApi.login({ email, password })
    setAuth(result.access_token, result.user)
    setToken(result.access_token)
    setUser(result.user)
    return result
  }, [])

  const register = useCallback(async (name, email, phone, password) => {
    const result = await authApi.register({ name, email, phone, password })
    setAuth(result.access_token, result.user)
    setToken(result.access_token)
    setUser(result.user)
    return result
  }, [])

  const logout = useCallback(() => {
    clearAuth()
    setUser(null)
    setToken(null)
    if (wsConnection) wsConnection.close()
  }, [wsConnection])

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!token && !!user,
    isAdmin: user?.role === 'admin',
    isUser: user?.role === 'user',
    login,
    register,
    logout,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
