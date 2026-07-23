/**
 * API client with JWT token interceptor for the Paper Trading platform.
 * All API calls go through this module.
 */

const getApiBase = () => {
  let url = import.meta.env.VITE_API_URL || ''
  url = url.replace(/\/+$/, '')
  return url
}

const API_BASE = getApiBase()

// Token management
const TOKEN_KEY = 'pt_access_token'
const USER_KEY = 'pt_user'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const getUser = () => {
  const raw = localStorage.getItem(USER_KEY)
  return raw ? JSON.parse(raw) : null
}
export const setAuth = (token, user) => {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}
export const clearAuth = () => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

/**
 * Make an authenticated API call.
 */
export async function apiFetch(path, options = {}) {
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  let response
  try {
    response = await fetch(url, {
      ...options,
      headers,
    })
  } catch (netErr) {
    throw new Error('Network error: Server is starting up or unreachable. Please try again in a few seconds.')
  }

  if (response.status === 401) {
    clearAuth()
    window.location.href = '/login'
    throw new Error('Session expired')
  }

  if (!response.ok) {
    let detail = ''
    try {
      const err = await response.json()
      detail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail || err)
    } catch {
      const text = await response.text().catch(() => '')
      detail = text || `Server Error (${response.status})`
    }
    throw new Error(detail || `Request failed: ${response.status}`)
  }

  return response.json()
}

// Auth API
export const authApi = {
  register: (data) => apiFetch('/api/pt/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  login: (data) => apiFetch('/api/pt/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  me: () => apiFetch('/api/pt/auth/me'),
}

// Strategy API
export const strategyApi = {
  list: (status) => apiFetch(`/api/pt/strategies/${status ? `?status=${status}` : ''}`),
  get: (id) => apiFetch(`/api/pt/strategies/${id}`),
  create: (data) => apiFetch('/api/pt/strategies/', { method: 'POST', body: JSON.stringify(data) }),
  activate: (id) => apiFetch(`/api/pt/strategies/${id}/activate`, { method: 'POST' }),
  reuse: (id) => apiFetch(`/api/pt/strategies/${id}/reuse`, { method: 'POST' }),
  exitLeg: (stratId, legId) => apiFetch(`/api/pt/strategies/${stratId}/legs/${legId}/exit`, { method: 'POST' }),
  exitAll: (id) => apiFetch(`/api/pt/strategies/${id}/exit-all`, { method: 'POST' }),
  close: (id) => apiFetch(`/api/pt/strategies/${id}/close`, { method: 'POST' }),
  delete: (id) => apiFetch(`/api/pt/strategies/${id}`, { method: 'DELETE' }),
  updateTimes: (id, payload) => apiFetch(`/api/pt/strategies/${id}/times`, { method: 'PUT', body: JSON.stringify(payload) }),
}

// Wallet API
export const walletApi = {
  get: () => apiFetch('/api/pt/wallet/'),
  transactions: (skip = 0, limit = 50) => apiFetch(`/api/pt/wallet/transactions?skip=${skip}&limit=${limit}`),
}

// History API
export const historyApi = {
  trades: (params) => {
    const qs = new URLSearchParams(params).toString()
    return apiFetch(`/api/pt/history/trades?${qs}`)
  },
  stats: () => apiFetch('/api/pt/history/stats'),
  dailyStats: () => apiFetch('/api/pt/history/daily-stats'),
  closedStrategies: (params) => {
    const qs = new URLSearchParams(params).toString()
    return apiFetch(`/api/pt/history/closed-strategies?${qs}`)
  },
}

// Admin API
export const adminApi = {
  users: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return apiFetch(`/api/pt/admin/users?${qs}`)
  },
  userDetail: (id) => apiFetch(`/api/pt/admin/users/${id}`),
  updateStatus: (id, status) => apiFetch(`/api/pt/admin/users/${id}/status`, {
    method: 'PUT', body: JSON.stringify({ status }),
  }),
  addChips: (userId, data) => apiFetch(`/api/pt/admin/users/${userId}/chips/add`, {
    method: 'POST', body: JSON.stringify(data),
  }),
  removeChips: (userId, data) => apiFetch(`/api/pt/admin/users/${userId}/chips/remove`, {
    method: 'POST', body: JSON.stringify(data),
  }),
  overview: () => apiFetch('/api/pt/admin/overview'),
  allStrategies: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return apiFetch(`/api/pt/admin/strategies?${qs}`)
  },
}

export const marketsApi = {
  indices: () => apiFetch('/api/pt/markets/indices'),
  expiries: (underlying) => apiFetch(`/api/pt/markets/expiries?underlying=${underlying}`),
  optionChain: (underlying, expiry) => 
    apiFetch(`/api/pt/markets/option-chain?underlying=${underlying}&expiry=${expiry}`),
}

// WebSocket
export function connectWebSocket(token, onMessage) {
  let wsBase = API_BASE ? API_BASE.replace(/^http/, 'ws') : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
  const ws = new WebSocket(`${wsBase}/ws/pt/${token}`)

  ws.onopen = () => {
    console.log('WebSocket connected')
  }
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch (e) {
      console.error('WS message parse error:', e)
    }
  }
  ws.onclose = () => {
    console.log('WebSocket disconnected')
    // Auto-reconnect after 3 seconds
    setTimeout(() => {
      if (getToken()) {
        connectWebSocket(getToken(), onMessage)
      }
    }, 3000)
  }
  ws.onerror = (err) => {
    console.error('WebSocket error:', err)
  }

  // Heartbeat
  const heartbeat = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }))
    }
  }, 30000)

  return {
    ws,
    close: () => {
      clearInterval(heartbeat)
      ws.close()
    },
  }
}
