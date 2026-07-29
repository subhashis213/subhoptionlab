package com.example.subhoptionlab.network

import android.util.Log
import com.google.gson.Gson
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.*
import java.util.concurrent.TimeUnit

data class MarketTick(
    val instrument_key: String? = null,
    val ltp: Double? = null,
    val last_price: Double? = null,
    val net_change: Double? = null,
    val change_percent: Double? = null,
    val close_price: Double? = null,
    val volume: Long? = null,
    val oi: Long? = null
)

class MarketStreamService private constructor() {
    private val client = OkHttpClient.Builder()
        .readTimeout(10, TimeUnit.SECONDS)
        .pingInterval(15, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()
    private var webSocket: WebSocket? = null
    private val scope = CoroutineScope(Dispatchers.IO)

    private val _liveDataMap = MutableStateFlow<Map<String, MarketTick>>(emptyMap())
    val liveDataMap: StateFlow<Map<String, MarketTick>> = _liveDataMap.asStateFlow()

    private val subscribedKeys = mutableSetOf<String>()

    fun connect() {
        if (webSocket != null) return

        val request = Request.Builder()
            .url("wss://subhoptionlab-7r1l.onrender.com/ws/live-market")
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d("MarketStream", "✅ Connected to WebSocket")
                if (subscribedKeys.isNotEmpty()) {
                    sendSubscription(subscribedKeys.toList())
                }
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    val tick = gson.fromJson(text, MarketTick::class.java)
                    val key = tick.instrument_key ?: return
                    val ltp = tick.ltp ?: tick.last_price ?: return

                    scope.launch {
                        val current = _liveDataMap.value.toMutableMap()
                        current[key] = tick
                        _liveDataMap.value = current
                    }
                } catch (e: Exception) {
                    // Ignore parse errors
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e("MarketStream", "WS Failure: ${t.message}")
                this@MarketStreamService.webSocket = null
                // Reconnect after 3 seconds
                scope.launch {
                    kotlinx.coroutines.delay(3000)
                    connect()
                }
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.d("MarketStream", "WS Closed: $reason")
                this@MarketStreamService.webSocket = null
            }
        })
    }

    fun subscribe(keys: List<String>) {
        if (keys.isEmpty()) return
        val newKeys = keys.filter { !subscribedKeys.contains(it) }
        if (newKeys.isNotEmpty()) {
            subscribedKeys.addAll(newKeys)
            sendSubscription(subscribedKeys.toList())
        }
    }

    private fun sendSubscription(keys: List<String>) {
        val payload = mapOf("action" to "subscribe", "keys" to keys)
        val json = gson.toJson(payload)
        webSocket?.send(json)
    }

    companion object {
        val instance by lazy { MarketStreamService() }
    }
}
