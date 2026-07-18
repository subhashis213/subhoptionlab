"""
Download 1-minute Upstox candle data for ALL trade dates and ATM strikes
that have bhavcopy data but no minute files yet.

This script is called on Render startup to ensure the deployed version
has the same real Upstox minute data as localhost.
"""

import os
import sys
import math
from datetime import date, timedelta
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from config import PARQUET_DIR, STRIKE_INTERVALS, SYMBOLS


def get_access_token() -> str:
    """Get Upstox access token from .env file or environment variable."""
    env_file = backend_dir / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                if line.strip().startswith("UPSTOX_ACCESS_TOKEN="):
                    return line.strip().split("=", 1)[1].strip()
    return os.environ.get("UPSTOX_ACCESS_TOKEN", "")


def get_dates_needing_minute_data(symbol: str) -> list[tuple[date, float]]:
    """
    Find all (trade_date, atm_strike) pairs from daily OHLC parquet
    that don't already have minute parquet files.
    Only includes dates that have real bhavcopy CSV data (not synthetic historical dates).
    """
    import polars as pl
    from config import RAW_DIR

    # First, determine which dates have REAL bhavcopy data
    real_dates = set()
    if RAW_DIR.exists():
        for csv_file in RAW_DIR.glob("*.csv"):
            # Extract date from filename like BhavCopy_NSE_FO_0_0_0_20260717_F_0000.csv
            name = csv_file.stem
            for part in name.split("_"):
                if len(part) == 8 and part.isdigit():
                    try:
                        from datetime import date as dt_date
                        d = dt_date(int(part[:4]), int(part[4:6]), int(part[6:8]))
                        real_dates.add(d)
                    except ValueError:
                        pass

    if not real_dates:
        print(f"  No real bhavcopy dates found for minute download")
        return []

    minute_dir = PARQUET_DIR / "minute" / symbol
    existing_minute_files = set()
    if minute_dir.exists():
        for f in minute_dir.glob("*.parquet"):
            existing_minute_files.add(f.stem.rsplit("_", 1)[0].rsplit("_", 1)[0])
            # e.g. "2026-07-17" from "2026-07-17_58500_CE.parquet"

    # Read underlying data to get spot prices per date, but ONLY for real bhavcopy dates
    results = []
    underlying_dir = PARQUET_DIR / "underlying" / symbol
    if not underlying_dir.exists():
        return []

    for pfile in underlying_dir.glob("*.parquet"):
        df = pl.read_parquet(pfile)
        for row in df.iter_rows(named=True):
            td = row["trade_date"]
            if isinstance(td, str):
                td = date.fromisoformat(td)

            if td not in real_dates:
                continue  # Skip synthetic/historical dates

            date_str = td.isoformat()
            if date_str in existing_minute_files:
                continue  # Already have minute data

            settle = row.get("settle_price") or row.get("close")
            if settle and settle > 0:
                step = STRIKE_INTERVALS.get(symbol, 100)
                atm = round(settle / step) * step
                results.append((td, float(atm)))

    return sorted(results, key=lambda x: x[0])


def download_minute_for_date(symbol: str, trade_date: date, atm_strike: float, access_token: str) -> bool:
    """Download 1-minute candles for CE and PE at ATM strike for a specific date."""
    try:
        from scripts.download_upstox_1min import (
            get_instrument_master,
            lookup_instrument_key,
            fetch_upstox_intraday_candles,
            save_minute_parquet,
        )
    except ImportError:
        print(f"Cannot import download_upstox_1min module")
        return False

    # We cache the master to avoid re-downloading for each date
    if not hasattr(download_minute_for_date, "_master"):
        print("Downloading Upstox instrument master (one-time)...")
        download_minute_for_date._master = get_instrument_master()
        print(f"  Loaded {len(download_minute_for_date._master)} instruments")

    master = download_minute_for_date._master
    date_str = trade_date.isoformat()
    success = True

    for option_type in ["CE", "PE"]:
        key = lookup_instrument_key(master, symbol, atm_strike, option_type, date_str)
        if not key:
            print(f"  ⚠️ No instrument key for {symbol} {int(atm_strike)} {option_type} on {date_str}")
            success = False
            continue

        try:
            candles = fetch_upstox_intraday_candles(key, date_str, date_str)
            if candles:
                save_minute_parquet(symbol, trade_date, atm_strike, option_type, candles)
            else:
                print(f"  ⚠️ No candles returned for {symbol} {int(atm_strike)} {option_type} on {date_str}")
                success = False
        except Exception as e:
            print(f"  ❌ Error downloading {option_type}: {e}")
            success = False

    return success


def main():
    access_token = get_access_token()
    if not access_token:
        print("⚠️ UPSTOX_ACCESS_TOKEN not set. Skipping minute data download.")
        print("   Minute data will use synthetic Brownian bridge simulation from daily OHLC.")
        return

    for symbol in SYMBOLS:
        print(f"\n{'='*50}")
        print(f"Checking {symbol} for missing minute data...")
        needs = get_dates_needing_minute_data(symbol)
        if not needs:
            print(f"  ✅ All dates already have minute data (or no daily data exists)")
            continue

        print(f"  Found {len(needs)} dates needing minute download")
        for td, atm in needs:
            print(f"\n  Downloading {symbol} {td} ATM={int(atm)}...")
            download_minute_for_date(symbol, td, atm, access_token)

    print("\n✅ Minute data sync complete!")


if __name__ == "__main__":
    main()
