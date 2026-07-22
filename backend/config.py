"""
Central configuration for the Options Backtester.
All paths, constants, and settings live here.
"""

from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent  # backtest/
BACKEND_ROOT = Path(__file__).parent          # backtest/backend/

RAW_DIR = PROJECT_ROOT / "raw_bhavcopies"
PARQUET_DIR = BACKEND_ROOT / "parquet_data"
DATA_DIR = BACKEND_ROOT / "data"

# Ensure directories exist
RAW_DIR.mkdir(parents=True, exist_ok=True)
PARQUET_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Symbols & Instruments ──────────────────────────────────────────────────────
SYMBOLS = ["BANKNIFTY", "NIFTY", "FINNIFTY"]

# Strike price step size for each index
STRIKE_INTERVALS = {
    "BANKNIFTY": 100,
    "NIFTY": 50,
    "FINNIFTY": 50,
}

# Weekly expiry day for each index (0=Monday, ..., 6=Sunday)
# These changed over time — the expiry resolver handles historical shifts.
# This is the "current" default for reference.
EXPIRY_WEEKDAYS = {
    "BANKNIFTY": 2,  # Wednesday (was Wed until Apr 2024, then Tue — handled in resolver)
    "NIFTY": 3,       # Thursday
    "FINNIFTY": 1,    # Tuesday (discontinued Nov 2024)
}

# ── NSE Bhavcopy URLs ─────────────────────────────────────────────────────────
# Legacy format (before July 8, 2024)
LEGACY_BHAVCOPY_URL = (
    "https://nsearchives.nseindia.com/content/historical/DERIVATIVES"
    "/{year}/{month_upper}/fo{dd}{month_upper}{year}bhav.csv.zip"
)

# UDiFF format (July 8, 2024 onwards)
UDIFF_BHAVCOPY_URL = (
    "https://nsearchives.nseindia.com/content/fo"
    "/BhavCopy_NSE_FO_0_0_0_{date_compact}_F_0000.csv.zip"
)

# Date when NSE switched from legacy to UDiFF format
UDIFF_CUTOVER_DATE = "2024-07-08"

# NSE session URL (hit this first to get cookies)
NSE_BASE_URL = "https://www.nseindia.com"

# ── Lot Sizes (per underlying) ────────────────────────────────────────────────
LOT_SIZES = {
    "NIFTY": 75,
    "BANKNIFTY": 15,
    "FINNIFTY": 25,
    "MIDCAPNIFTY": 50,
}

# ── Market Hours (IST) ────────────────────────────────────────────────────────
MARKET_OPEN = "09:15"
MARKET_CLOSE = "15:30"

# ── Paper Trade Safety ─────────────────────────────────────────────────────────
# Informational only — actual enforcement is structural in upstox_guard.py.
# There is NO code path to Upstox's order placement endpoints anywhere.
PAPER_TRADE_ONLY = True

import os

# ── Database ───────────────────────────────────────────────────────────────────
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "option_backtester")
