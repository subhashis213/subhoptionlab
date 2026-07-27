import { useEffect, useRef, useState, useCallback } from 'react'

let globalWs = null;
let reconnectTimeout = null;
let connectionCount = 0;
let subscriptionKeys = new Set();
let subscribers = new Set();
let isConnecting = false;

/**
 * Get the correct WebSocket URL.
 * CRITICAL: Vercel cannot proxy WebSockets. We must connect directly to Render backend.
 * On production: wss://subhoptionlab.onrender.com
 * On localhost: ws://localhost:8000
 */
function getWsUrl() {
  // If user explicitly set a WS URL, use it
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  
  // On production (not localhost), connect directly to Render backend
  if (typeof window !== 'undefined' && 
      window.location.hostname !== 'localhost' && 
      window.location.hostname !== '127.0.0.1') {
    return 'wss://subhoptionlab.onrender.com';
  }
  
  // Local dev
  return 'ws://localhost:8000';
}

function connectWs() {
  if (globalWs || isConnecting) return;
  isConnecting = true;

  const WS_URL = getWsUrl();

  try {
    console.log(`[MarketStream] Connecting to ${WS_URL}/ws/live-market`);
    globalWs = new WebSocket(`${WS_URL}/ws/live-market`);
    
    globalWs.onopen = () => {
      console.log("[MarketStream] ✅ Connected to Live Market WebSocket.");
      isConnecting = false;
      // Resubscribe to all active keys
      if (subscriptionKeys.size > 0) {
        globalWs.send(JSON.stringify({ action: "subscribe", keys: Array.from(subscriptionKeys) }));
      }
    };
    
    globalWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "pong") return;
        
        // Notify all hooked components
        for (const cb of subscribers) {
          cb(msg);
        }
      } catch (err) {
        console.error("[MarketStream] WS Parse error", err);
      }
    };
    
    globalWs.onclose = (e) => {
      globalWs = null;
      isConnecting = false;
      console.log(`[MarketStream] WebSocket closed (code: ${e.code}). Reconnecting in 3s...`);
      clearTimeout(reconnectTimeout);
      reconnectTimeout = setTimeout(connectWs, 3000);
    };
    
    globalWs.onerror = (err) => {
      console.error("[MarketStream] WebSocket Error:", err);
      if (globalWs) globalWs.close();
    };
    
  } catch (err) {
    console.error("[MarketStream] WebSocket setup error:", err);
    isConnecting = false;
    reconnectTimeout = setTimeout(connectWs, 3000);
  }
}

function disconnectWs() {
  clearTimeout(reconnectTimeout);
  if (globalWs && connectionCount <= 0) {
    globalWs.close();
    globalWs = null;
    isConnecting = false;
  }
}

export default function useMarketStream(keysToSubscribe = []) {
  const [marketData, setMarketData] = useState({});
  const bufferRef = useRef({});
  const animationFrameRef = useRef(null);

  const handleMessage = useCallback((msg) => {
    let instrumentKey = msg.instrument_key;
    let ltp = null;
    
    // Handle Upstox Protobuf/dict structure
    if (msg.ff) {
      if (msg.ff.indexFF && msg.ff.indexFF.ltpc) {
        ltp = msg.ff.indexFF.ltpc.ltp;
        if (!instrumentKey && msg.ff.indexFF.ltpc.instrument_key) {
          instrumentKey = msg.ff.indexFF.ltpc.instrument_key;
        }
      } else if (msg.ff.marketFF && msg.ff.marketFF.ltpc) {
        ltp = msg.ff.marketFF.ltpc.ltp;
        if (!instrumentKey && msg.ff.marketFF.ltpc.instrument_key) {
          instrumentKey = msg.ff.marketFF.ltpc.instrument_key;
        }
      }
    }
    
    // API fallback dict from backend
    if (msg.last_price !== undefined) {
      ltp = msg.last_price;
    }

    if (ltp !== null && instrumentKey) {
      bufferRef.current[instrumentKey] = msg;
    }
    
    // Throttle rendering at ~30 FPS using requestAnimationFrame
    if (!animationFrameRef.current) {
      animationFrameRef.current = requestAnimationFrame(() => {
        setMarketData(prev => ({...prev, ...bufferRef.current}));
        bufferRef.current = {};
        animationFrameRef.current = null;
      });
    }
  }, []);

  useEffect(() => {
    subscribers.add(handleMessage);
    
    connectionCount++;
    if (connectionCount === 1) {
      connectWs();
    }
    
    // Subscribe to new keys when WS is ready
    if (keysToSubscribe.length > 0) {
      const newKeys = keysToSubscribe.filter(k => !subscriptionKeys.has(k));
      newKeys.forEach(k => subscriptionKeys.add(k));
      
      if (globalWs && globalWs.readyState === WebSocket.OPEN && newKeys.length > 0) {
        globalWs.send(JSON.stringify({ action: "subscribe", keys: newKeys }));
      }
    }
    
    return () => {
      subscribers.delete(handleMessage);
      connectionCount--;
      if (connectionCount <= 0) {
        connectionCount = 0;
        disconnectWs();
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [keysToSubscribe.join(","), handleMessage]);

  return marketData;
}
