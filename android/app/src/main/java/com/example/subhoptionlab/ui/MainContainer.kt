package com.example.subhoptionlab.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.ShowChart
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

enum class AppTab {
    HOME, MARKETS, STRATEGIES, WALLET, PROFILE
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainContainer() {
    var selectedTab by remember { mutableStateOf(AppTab.HOME) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.clickable { selectedTab = AppTab.HOME }
                    ) {
                        Text("卐", fontSize = 24.sp, color = Color(0xFFFFCC00))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("शुभमुहूर्त Subh Muhurat", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color(0xFF0F172A))
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White)
            )
        },
        bottomBar = {
            NavigationBar(containerColor = Color.White, tonalElevation = 8.dp) {
                NavigationBarItem(
                    selected = selectedTab == AppTab.HOME,
                    onClick = { selectedTab = AppTab.HOME },
                    icon = { Icon(Icons.Default.Home, contentDescription = "Home") },
                    label = { Text("Home") },
                    colors = NavigationBarItemDefaults.colors(selectedIconColor = Color(0xFF2563EB), indicatorColor = Color(0xFF2563EB).copy(alpha = 0.12f))
                )
                NavigationBarItem(
                    selected = selectedTab == AppTab.MARKETS,
                    onClick = { selectedTab = AppTab.MARKETS },
                    icon = { Icon(Icons.Default.TrendingUp, contentDescription = "Markets") },
                    label = { Text("Markets") },
                    colors = NavigationBarItemDefaults.colors(selectedIconColor = Color(0xFF2563EB), indicatorColor = Color(0xFF2563EB).copy(alpha = 0.12f))
                )
                NavigationBarItem(
                    selected = selectedTab == AppTab.STRATEGIES,
                    onClick = { selectedTab = AppTab.STRATEGIES },
                    icon = { Icon(Icons.Default.ShowChart, contentDescription = "Strategies") },
                    label = { Text("Strategies") },
                    colors = NavigationBarItemDefaults.colors(selectedIconColor = Color(0xFF2563EB), indicatorColor = Color(0xFF2563EB).copy(alpha = 0.12f))
                )
                NavigationBarItem(
                    selected = selectedTab == AppTab.WALLET,
                    onClick = { selectedTab = AppTab.WALLET },
                    icon = { Icon(Icons.Default.AccountBalanceWallet, contentDescription = "Wallet") },
                    label = { Text("Wallet") },
                    colors = NavigationBarItemDefaults.colors(selectedIconColor = Color(0xFF2563EB), indicatorColor = Color(0xFF2563EB).copy(alpha = 0.12f))
                )
                NavigationBarItem(
                    selected = selectedTab == AppTab.PROFILE,
                    onClick = { selectedTab = AppTab.PROFILE },
                    icon = { Icon(Icons.Default.Person, contentDescription = "Profile") },
                    label = { Text("Profile") },
                    colors = NavigationBarItemDefaults.colors(selectedIconColor = Color(0xFF2563EB), indicatorColor = Color(0xFF2563EB).copy(alpha = 0.12f))
                )
            }
        }
    ) { paddingValues ->
        Box(modifier = Modifier.padding(paddingValues)) {
            when (selectedTab) {
                AppTab.HOME -> HomeScreen(
                    onNavigateToMarkets = { selectedTab = AppTab.MARKETS },
                    onNavigateToStrategies = { selectedTab = AppTab.STRATEGIES }
                )
                AppTab.MARKETS -> MarketsScreen()
                AppTab.STRATEGIES -> StrategiesScreen()
                AppTab.WALLET -> WalletScreen()
                AppTab.PROFILE -> ProfileScreen()
            }
        }
    }
}
