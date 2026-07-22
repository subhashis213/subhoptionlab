"""
Automatic Daily Market Data Synchronizer.

Automatically checks for any missing trade dates between the last downloaded date 
and today. Downloads missing NSE Bhavcopies, updates Parquet stores, and downloads 
1-minute Upstox candle data.
"""

import logging
import threading
import requests
import zipfile
import io
from datetime import date, datetime, timedelta
from pathlib import Path

from config import RAW_DIR, PARQUET_DIR

logger = logging.getLogger(__name__)


def auto_sync_market_data():
    """Check for missing trading dates up to today and download them automatically."""
    try:
        today = date.today()
        # Find latest downloaded date in raw_bhavcopies
        downloaded_dates = []
        if RAW_DIR.exists():
            for csv_file in RAW_DIR.glob("*.csv"):
                name = csv_file.stem
                for part in name.split("_"):
                    if len(part) == 8 and part.isdigit():
                        try:
                            d = date(int(part[:4]), int(part[4:6]), int(part[6:8]))
                            downloaded_dates.append(d)
                        except ValueError:
                            pass

        max_date = max(downloaded_dates) if downloaded_dates else date(2026, 7, 1)
        logger.info(f"AutoSync: Latest downloaded date is {max_date}. Checking for missing dates up to {today}...")

        # If max_date is before today, download missing range
        if max_date < today:
            start_date = max_date + timedelta(days=1)
            end_date = today
            logger.info(f"AutoSync: Syncing missing dates from {start_date} to {end_date}...")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                'Accept': '*/*'
            }
            curr = start_date
            downloaded_new = False

            while curr <= end_date:
                # Skip weekends
                if curr.weekday() < 5:
                    d_str = curr.strftime("%Y%m%d")
                    url = f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{d_str}_F_0000.csv.zip"
                    try:
                        res = requests.get(url, headers=headers, timeout=15)
                        if res.status_code == 200 and len(res.content) > 1000:
                            with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
                                csv_name = zf.namelist()[0]
                                out_path = RAW_DIR / csv_name
                                out_path.write_bytes(zf.read(csv_name))
                                logger.info(f"AutoSync: Successfully downloaded Bhavcopy for {curr}!")
                                downloaded_new = True
                    except Exception as err:
                        logger.warning(f"AutoSync: Failed to download for {curr}: {err}")
                curr += timedelta(days=1)

            if downloaded_new:
                # Parse new CSVs into Parquet
                logger.info("AutoSync: Parsing newly downloaded Bhavcopies into Parquet...")
                from data.parser import parse_all_bhavcopies
                from data.parquet_store import write_options_parquet, write_underlying_parquet
                options_df, futures_df = parse_all_bhavcopies(RAW_DIR)
                if not options_df.is_empty():
                    write_options_parquet(options_df)
                if not futures_df.is_empty():
                    write_underlying_parquet(futures_df)
                logger.info("AutoSync: Parquet stores updated!")

            # Sync 1-minute candle data for any missing dates
            logger.info("AutoSync: Syncing Upstox 1-minute candle data...")
            from scripts.download_all_minute_data import main as download_minute_main
            download_minute_main()
            logger.info("AutoSync: Daily market data sync completed successfully!")

    except Exception as e:
        logger.error("AutoSync error: %s", e)


def start_auto_sync_background():
    """Run auto sync in a background daemon thread."""
    thread = threading.Thread(target=auto_sync_market_data, daemon=True)
    thread.start()
