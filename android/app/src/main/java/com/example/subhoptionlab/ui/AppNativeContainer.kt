package com.example.subhoptionlab.ui

import android.annotation.SuppressLint
import android.graphics.Bitmap
import android.view.ViewGroup
import android.webkit.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ExitToApp
import androidx.compose.material.icons.automirrored.filled.ShowChart
import androidx.compose.material.icons.automirrored.filled.TrendingUp
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView

enum class NativeTab(val route: String) {
    HOME("https://subhoptionlab.vercel.app/home"),
    MARKETS("https://subhoptionlab.vercel.app/markets"),
    STRATEGIES("https://subhoptionlab.vercel.app/strategies"),
    WALLET("https://subhoptionlab.vercel.app/wallet"),
    PROFILE("https://subhoptionlab.vercel.app/profile")
}

@OptIn(ExperimentalMaterial3Api::class)
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun AppNativeContainer() {
    var selectedTab by remember { mutableStateOf(NativeTab.HOME) }
    var webViewRef by remember { mutableStateOf<WebView?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var progress by remember { mutableStateOf(0) }
    var currentPath by remember { mutableStateOf("/login") } // start at login by default if it's the first screen
    var currentTheme by remember { mutableStateOf("light") } // Syncs with web app theme

    val showNativeNav = !currentPath.contains("/login") && !currentPath.contains("/register")

    val isDark = currentTheme == "dark"
    val navBgColor = if (isDark) Color(0xFF0F172A) else Color.White
    val navTextColor = if (isDark) Color.White else Color(0xFF0F172A)
    val unselectedColor = if (isDark) Color(0xFF94A3B8) else Color(0xFF64748B)
    val selectedColor = if (isDark) Color(0xFF3B82F6) else Color(0xFF2563EB)
    val bgColor = if (isDark) Color(0xFF0F172A) else Color(0xFFF8FAFC)

    Scaffold(
        topBar = {
            if (showNativeNav) {
                TopAppBar(
                    title = {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.clickable {
                                selectedTab = NativeTab.HOME
                                webViewRef?.evaluateJavascript("window.dispatchEvent(new CustomEvent('native-navigate', { detail: { path: '/home' } }))", null)
                            }
                        ) {
                            Text("卐", fontSize = 24.sp, color = Color(0xFFFFCC00))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                "Subh Muhurat",
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold,
                                color = navTextColor
                            )
                        }
                    },
                    actions = {
                        IconButton(
                            onClick = {
                                webViewRef?.evaluateJavascript(
                                    "localStorage.clear(); sessionStorage.clear(); window.location.href='/login';",
                                    null
                                )
                            }
                        ) {
                            Icon(
                                imageVector = Icons.AutoMirrored.Filled.ExitToApp,
                                contentDescription = "Logout",
                                tint = Color(0xFFEF4444) // red-500
                            )
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = navBgColor)
                )
            }
        },
        bottomBar = {
            if (showNativeNav) {
                NavigationBar(containerColor = navBgColor, tonalElevation = 8.dp) {
                    NavigationBarItem(
                        selected = selectedTab == NativeTab.HOME,
                        onClick = {
                            selectedTab = NativeTab.HOME
                            webViewRef?.evaluateJavascript("window.dispatchEvent(new CustomEvent('native-navigate', { detail: { path: '/home' } }))", null)
                        },
                        icon = { Icon(Icons.Default.Home, contentDescription = "Home") },
                        label = { Text("Home") },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = selectedColor,
                            unselectedIconColor = unselectedColor,
                            selectedTextColor = selectedColor,
                            unselectedTextColor = unselectedColor,
                            indicatorColor = selectedColor.copy(alpha = 0.15f)
                        )
                    )
                    NavigationBarItem(
                        selected = selectedTab == NativeTab.MARKETS,
                        onClick = {
                            selectedTab = NativeTab.MARKETS
                            webViewRef?.evaluateJavascript("window.dispatchEvent(new CustomEvent('native-navigate', { detail: { path: '/markets' } }))", null)
                        },
                        icon = { Icon(Icons.AutoMirrored.Filled.TrendingUp, contentDescription = "Markets") },
                        label = { Text("Markets") },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = selectedColor,
                            unselectedIconColor = unselectedColor,
                            selectedTextColor = selectedColor,
                            unselectedTextColor = unselectedColor,
                            indicatorColor = selectedColor.copy(alpha = 0.15f)
                        )
                    )
                    NavigationBarItem(
                        selected = selectedTab == NativeTab.STRATEGIES,
                        onClick = {
                            selectedTab = NativeTab.STRATEGIES
                            webViewRef?.evaluateJavascript("window.dispatchEvent(new CustomEvent('native-navigate', { detail: { path: '/strategies' } }))", null)
                        },
                        icon = { Icon(Icons.AutoMirrored.Filled.ShowChart, contentDescription = "Strategies") },
                        label = { Text("Strategies") },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = selectedColor,
                            unselectedIconColor = unselectedColor,
                            selectedTextColor = selectedColor,
                            unselectedTextColor = unselectedColor,
                            indicatorColor = selectedColor.copy(alpha = 0.15f)
                        )
                    )
                    NavigationBarItem(
                        selected = selectedTab == NativeTab.WALLET,
                        onClick = {
                            selectedTab = NativeTab.WALLET
                            webViewRef?.evaluateJavascript("window.dispatchEvent(new CustomEvent('native-navigate', { detail: { path: '/wallet' } }))", null)
                        },
                        icon = { Icon(Icons.Default.AccountBalanceWallet, contentDescription = "Wallet") },
                        label = { Text("Wallet") },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = selectedColor,
                            unselectedIconColor = unselectedColor,
                            selectedTextColor = selectedColor,
                            unselectedTextColor = unselectedColor,
                            indicatorColor = selectedColor.copy(alpha = 0.15f)
                        )
                    )
                    NavigationBarItem(
                        selected = selectedTab == NativeTab.PROFILE,
                        onClick = {
                            selectedTab = NativeTab.PROFILE
                            webViewRef?.evaluateJavascript("window.dispatchEvent(new CustomEvent('native-navigate', { detail: { path: '/profile' } }))", null)
                        },
                        icon = { Icon(Icons.Default.Person, contentDescription = "Profile") },
                        label = { Text("Profile") },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = selectedColor,
                            unselectedIconColor = unselectedColor,
                            selectedTextColor = selectedColor,
                            unselectedTextColor = unselectedColor,
                            indicatorColor = selectedColor.copy(alpha = 0.15f)
                        )
                    )
                }
            }
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .padding(paddingValues)
                .fillMaxSize()
                .background(bgColor)
        ) {
            if (isLoading) {
                LinearProgressIndicator(
                    progress = { progress / 100f },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(3.dp),
                    color = Color(0xFF2563EB),
                    trackColor = Color(0xFFE2E8F0)
                )
            }

            AndroidView(
                factory = { context ->
                    WebView(context).apply {
                        webViewRef = this
                        layoutParams = ViewGroup.LayoutParams(
                            ViewGroup.LayoutParams.MATCH_PARENT,
                            ViewGroup.LayoutParams.MATCH_PARENT
                        )

                        settings.apply {
                            javaScriptEnabled = true
                            domStorageEnabled = true
                            databaseEnabled = true
                            useWideViewPort = true
                            loadWithOverviewMode = true
                            setSupportMultipleWindows(true)
                            javaScriptCanOpenWindowsAutomatically = true
                            mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
                            userAgentString = userAgentString + " MobileNativeApp"
                        }

                        // Enable Cookies & Storage Persistence
                        val cookieManager = CookieManager.getInstance()
                        cookieManager.setAcceptCookie(true)
                        cookieManager.setAcceptThirdPartyCookies(this, true)

                        addJavascriptInterface(object {
                            @JavascriptInterface
                            fun updatePath(path: String) {
                                android.os.Handler(android.os.Looper.getMainLooper()).post {
                                    currentPath = path
                                    // Auto-select tab based on path
                                    when {
                                        path.contains("/home") -> selectedTab = NativeTab.HOME
                                        path.contains("/markets") -> selectedTab = NativeTab.MARKETS
                                        path.contains("/strategies") -> selectedTab = NativeTab.STRATEGIES
                                        path.contains("/wallet") -> selectedTab = NativeTab.WALLET
                                        path.contains("/profile") -> selectedTab = NativeTab.PROFILE
                                    }
                                }
                            }
                            
                            @JavascriptInterface
                            fun updateTheme(theme: String) {
                                android.os.Handler(android.os.Looper.getMainLooper()).post {
                                    currentTheme = theme
                                }
                            }
                        }, "AndroidApp")

                        webViewClient = object : WebViewClient() {
                            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                                super.onPageStarted(view, url, favicon)
                                isLoading = true
                            }

                            override fun onPageFinished(view: WebView?, url: String?) {
                                super.onPageFinished(view, url)
                                isLoading = false
                            }

                            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                                val reqUrl = request?.url?.toString() ?: return false
                                if (reqUrl.contains("upstox.com") || reqUrl.contains("subhoptionlab.vercel.app")) {
                                    view?.loadUrl(reqUrl)
                                    return true
                                }
                                return false
                            }
                        }

                        webChromeClient = object : WebChromeClient() {
                            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                                progress = newProgress
                                if (newProgress == 100) isLoading = false
                            }
                        }

                        loadUrl("https://subhoptionlab.vercel.app")
                    }
                },
                modifier = Modifier.fillMaxSize()
            )
        }
    }
}
