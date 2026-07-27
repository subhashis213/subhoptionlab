import { useEffect, useRef, useState, useCallback } from 'react'

// ── Global singleton WebSocket state ────────────────────────────────────────
let globalWs = null;
let reconnectTimeout = null;
let connectionCount = 0;
let subscriptionKeys = new Set();
let subscribers = new Set();
let isConnecting = false;

/**
 * Get the correct WebSocket base URL.
 * CRITICAL: Vercel CANNOT proxy WebSocket connections.
 * On production we connect directly to the Render backend.
 */
function getWsBase() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
  if (typeof window !== 'undefined' &&
      window.location.hostname !== 'localhost' &&
      window.location.hostname !== '127.0.0.1') {
    return 'wss://subhoptionlab.onrender.com';
  }
  return 'ws://localhost:8000';
}

function connectWs() {
  if (globalWs || isConnecting) return;
  isConnecting = true;

  const wsBase = getWsBase();
  const url = `${wsBase}/ws/live-market`;

  try {
    console.log(`[MarketStream] Connecting → ${url}`);
    globalWs = new WebSocket(url);

    globalWs.onopen = () => {
      console.log('[MarketStream] ✅ Connected');
      isConnecting = false;
      if (subscriptionKeys.size > 0) {
        globalWs.send(JSON.stringify({ action: 'subscribe', keys: Array.from(subscriptionKeys) }));
      }
    };

    globalWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'pong') return;
        for (const cb of subscribers) {
          cb(msg);
        }
      } catch (err) {
        console.error('[MarketStream] Parse error:', err);
      }
    };

    globalWs.onclose = (e) => {
      globalWs = null;
      isConnecting = false;
      console.log(`[MarketStream] Closed (${e.code}). Reconnecting in 2s...`);
      clearTimeout(reconnectTimeout);
      if (connectionCount > 0) {
        reconnectTimeout = setTimeout(connectWs, 2000);
      }
    };

    globalWs.onerror = () => {
      if (globalWs) globalWs.close();
    };

  } catch (err) {
    console.error('[MarketStream] Setup error:', err);
    isConnecting = false;
    reconnectTimeout = setTimeout(connectWs, 3000);
  }
}

function disconnectWs() {
  clearTimeout(reconnectTimeout);
  if (globalWs) {
    globalWs.close();
    globalWs = null;
    isConnecting = false;
  }
}

function subscribeKeys(keys) {
  const newKeys = keys.filter(k => !subscriptionKeys.has(k));
  newKeys.forEach(k => subscriptionKeys.add(k));
  if (globalWs && globalWs.readyState === WebSocket.OPEN && newKeys.length > 0) {
    globalWs.send(JSON.stringify({ action: 'subscribe', keys: newKeys }));
  }
}

// ── Hook ─────────────────────────────────────────────────────────────────────
export default function useMarketStream(keysToSubscribe = []) {
  const [marketData, setMarketData] = useState({});
  const bufferRef = useRef({});
  const rafRef = useRef(null);

  const handleMessage = useCallback((msg) => {
    /**
     * Backend now sends one flat object per instrument:
     * {
     *   instrument_key: "NSE_INDEX|Nifty Bank",
     *   last_price: 57120.7,
     *   ltp: 57120.7,
     *   net_change: 230.5,
     *   change_percent: 0.41,
     *   close_price: 56890.2,
     *   volume: 123456,   (optional)
     *   oi: 98765,        (optional)
     * }
     */
    const key = msg.instrument_key;
    const ltp = msg.ltp ?? msg.last_price;

    if (!key || ltp === undefined || ltp === null) return;

    bufferRef.current[key] = msg;

    // Flush to state at ~60 FPS
    if (!rafRef.current) {
      rafRef.current = requestAnimationFrame(() => {
        setMarketData(prev => ({ ...prev, ...bufferRef.current }));
        bufferRef.current = {};
        rafRef.current = null;
      });
    }
  }, []);

  // Subscribe / unsubscribe when keysToSubscribe changes
  useEffect(() => {
    subscribers.add(handleMessage);
    connectionCount++;

    if (connectionCount === 1) {
      connectWs();
    }

    if (keysToSubscribe.length > 0) {
      subscribeKeys(keysToSubscribe);
    }

    return () => {
      subscribers.delete(handleMessage);
      connectionCount--;
      if (connectionCount <= 0) {
        connectionCount = 0;
        disconnectWs();
      }
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keysToSubscribe.join(','), handleMessage]);

  return marketData;
}
