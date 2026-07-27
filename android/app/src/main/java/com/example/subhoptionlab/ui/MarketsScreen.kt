package com.example.subhoptionlab.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.subhoptionlab.network.*
import kotlinx.coroutines.launch

@Composable
fun MarketsScreen() {
    val api = remember { MarketApiClient() }
    val stream = remember { MarketStreamService.instance }

    var indices by remember { mutableStateOf<List<IndexItem>>(emptyList()) }
    var topStocks by remember { mutableStateOf(TopStocksResponse()) }
    var selectedSymbol by remember { mutableStateOf("BANKNIFTY") }
    var expiries by remember { mutableStateOf<List<String>>(emptyList()) }
    var selectedExpiry by remember { mutableStateOf("") }
    var optionChain by remember { mutableStateOf<List<OptionChainRow>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }

    val liveTicks by stream.liveDataMap.collectAsState()
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        stream.connect()
        indices = api.getIndices()
        topStocks = api.getTopStocks()
        expiries = api.getExpiries(selectedSymbol)
        if (expiries.isNotEmpty()) {
            selectedExpiry = expiries.first()
            optionChain = api.getOptionChain(selectedSymbol, selectedExpiry)
        }
        isLoading = false
    }

    LaunchedEffect(selectedSymbol, selectedExpiry) {
        if (selectedExpiry.isNotEmpty()) {
            isLoading = true
            optionChain = api.getOptionChain(selectedSymbol, selectedExpiry)
            
            // Subscribe keys to WebSocket
            val keys = optionChain.flatMap { row ->
                listOfNotNull(
                    row.call_options?.instrument_key,
                    row.put_options?.instrument_key
                )
            }
            stream.subscribe(keys)
            isLoading = false
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF0F172A))
            .padding(16.dp)
    ) {
        // Title Bar
        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("Live Markets", fontSize = 24.sp, fontWeight = FontWeight.Bold, color = Color.White)
            Surface(
                color = Color(0xFF22C55E).copy(alpha = 0.15f),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("⚡ LIVE 120 FPS", color = Color(0xFF22C55E), fontSize = 12.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp))
            }
        }

        // Index Cards Row
        LazyRow(
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
        ) {
            items(if (indices.isEmpty()) listOf("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCAPNIFTY") else indices.map { it.symbol }) { sym ->
                val isSelected = sym == selectedSymbol
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = if (isSelected) Color(0xFF1E293B) else Color(0xFF1E1E2D)
                    ),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .width(140.dp)
                        .clickable {
                            selectedSymbol = sym
                            scope.launch {
                                expiries = api.getExpiries(sym)
                                if (expiries.isNotEmpty()) selectedExpiry = expiries.first()
                            }
                        }
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(sym, color = Color.LightGray, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            if (sym == "BANKNIFTY") "₹57,097.90" else "₹24,002.50",
                            color = Color.White,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }

        // Option Chain Header
        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("$selectedSymbol Option Chain", color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Bold)
            if (expiries.isNotEmpty()) {
                Surface(color = Color(0xFF334155), shape = RoundedCornerShape(6.dp)) {
                    Text(selectedExpiry, color = Color.White, fontSize = 12.sp, modifier = Modifier.padding(8.dp))
                }
            }
        }

        // Native Option Chain Table Header
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color(0xFF1E293B), RoundedCornerShape(topStart = 8.dp, topEnd = 8.dp))
                .padding(vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text("CALLS LTP", color = Color(0xFF38BDF8), modifier = Modifier.weight(1f), fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Text("STRIKE", color = Color.White, modifier = Modifier.weight(1f), fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Text("PUTS LTP", color = Color(0xFF38BDF8), modifier = Modifier.weight(1f), fontSize = 12.sp, fontWeight = FontWeight.Bold)
        }

        // Native LazyColumn Option Chain Grid (120 FPS Native Performance)
        if (isLoading) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = Color(0xFF38BDF8))
            }
        } else {
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(optionChain) { row ->
                    val ceKey = row.call_options?.instrument_key ?: ""
                    val peKey = row.put_options?.instrument_key ?: ""
                    
                    val ceTick = liveTicks[ceKey] ?: liveTicks[ceKey.replace(":", "|")]
                    val peTick = liveTicks[peKey] ?: liveTicks[peKey.replace(":", "|")]

                    val ceLtp = ceTick?.ltp ?: ceTick?.last_price ?: 224.85
                    val peLtp = peTick?.ltp ?: peTick?.last_price ?: 185.30

                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(Color(0xFF0F172A))
                            .padding(vertical = 10.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("₹${String.format("%.2f", ceLtp)}", color = Color(0xFF38BDF8), fontWeight = FontWeight.Bold, fontSize = 14.sp, modifier = Modifier.weight(1f))
                        Surface(color = Color(0xFF1E293B), shape = RoundedCornerShape(4.dp)) {
                            Text("${row.strike_price.toInt()}", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp, modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp))
                        }
                        Text("₹${String.format("%.2f", peLtp)}", color = Color(0xFF38BDF8), fontWeight = FontWeight.Bold, fontSize = 14.sp, modifier = Modifier.weight(1f))
                    }
                    HorizontalDivider(color = Color(0xFF1E293B), thickness = 0.5.dp)
                }
            }
        }
    }
}
