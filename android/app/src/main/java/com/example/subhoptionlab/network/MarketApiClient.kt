package com.example.subhoptionlab.network

import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

data class IndexItem(
    val symbol: String,
    val name: String,
    val ltp: Double = 0.0,
    val change: Double = 0.0,
    val change_percent: Double = 0.0
)

data class StockItem(
    val symbol: String,
    val name: String,
    val ltp: Double = 0.0,
    val change: Double = 0.0,
    val change_percent: Double = 0.0,
    val instrument_key: String = ""
)

data class TopStocksResponse(
    val gainers: List<StockItem> = emptyList(),
    val losers: List<StockItem> = emptyList()
)

data class OptionContract(
    val instrument_key: String = "",
    val market_data: Map<String, Any>? = null
)

data class OptionChainRow(
    val strike_price: Double,
    val call_options: OptionContract? = null,
    val put_options: OptionContract? = null
)

class MarketApiClient {
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()
    private val baseUrl = "https://subhoptionlab.onrender.com"

    suspend fun getIndices(): List<IndexItem> = withContext(Dispatchers.IO) {
        val request = Request.Builder().url("$baseUrl/api/pt/markets/indices").build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) return@withContext emptyList()
            val json = response.body?.string() ?: return@withContext emptyList()
            val type = object : TypeToken<List<IndexItem>>() {}.type
            gson.fromJson(json, type)
        }
    }

    suspend fun getTopStocks(): TopStocksResponse = withContext(Dispatchers.IO) {
        val request = Request.Builder().url("$baseUrl/api/pt/markets/top-stocks").build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) return@withContext TopStocksResponse()
            val json = response.body?.string() ?: return@withContext TopStocksResponse()
            gson.fromJson(json, TopStocksResponse::class.java)
        }
    }

    suspend fun getExpiries(symbol: String): List<String> = withContext(Dispatchers.IO) {
        val request = Request.Builder().url("$baseUrl/api/pt/markets/expiries?underlying=$symbol").build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) return@withContext listOf("2026-07-28")
            val json = response.body?.string() ?: return@withContext listOf("2026-07-28")
            val type = object : TypeToken<List<String>>() {}.type
            gson.fromJson(json, type)
        }
    }

    suspend fun getOptionChain(underlying: String, expiry: String): List<OptionChainRow> = withContext(Dispatchers.IO) {
        val request = Request.Builder().url("$baseUrl/api/pt/markets/option-chain?underlying=$underlying&expiry=$expiry").build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) return@withContext emptyList()
            val json = response.body?.string() ?: return@withContext emptyList()
            val type = object : TypeToken<List<OptionChainRow>>() {}.type
            gson.fromJson(json, type)
        }
    }
}
