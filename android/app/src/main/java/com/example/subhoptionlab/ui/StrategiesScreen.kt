package com.example.subhoptionlab.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun StrategiesScreen() {
    var strategyName by remember { mutableStateOf("NIFTY Straddle") }
    var underlying by remember { mutableStateOf("NIFTY") }
    var isAutoTradeEnabled by remember { mutableStateOf(false) }
    var isStopLossEnabled by remember { mutableStateOf(true) }
    var scheduledTime by remember { mutableStateOf("09:20 AM") }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF8FAFC))
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text("Options Strategy Builder", color = Color(0xFF0F172A), fontSize = 22.sp, fontWeight = FontWeight.Bold)
        }

        // Strategy Config Card
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = Color.White),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text("STRATEGY CONFIGURATION", color = Color(0xFF64748B), fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.height(12.dp))

                    OutlinedTextField(
                        value = strategyName,
                        onValueChange = { strategyName = it },
                        label = { Text("Strategy Name") },
                        modifier = Modifier.fillMaxWidth()
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    // Standard Android Native Material3 Switch controls
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text("Scheduled Auto-Trade", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                            Text("Auto execute at specified market time", color = Color(0xFF64748B), fontSize = 12.sp)
                        }
                        Switch(
                            checked = isAutoTradeEnabled,
                            onCheckedChange = { isAutoTradeEnabled = it },
                            colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = Color(0xFF2563EB))
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text("Stop Loss & Target Guard", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                            Text("Auto exit legs when SL or Target hits", color = Color(0xFF64748B), fontSize = 12.sp)
                        }
                        Switch(
                            checked = isStopLossEnabled,
                            onCheckedChange = { isStopLossEnabled = it },
                            colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = Color(0xFF059669))
                        )
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    Button(
                        onClick = { },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2563EB)),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier.fillMaxWidth().height(48.dp)
                    ) {
                        Text("Create & Deploy Strategy", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}
