"""
Main pipeline script for the Options Backtester data layer.

Usage:
    # Download bhavcopies for a date range, parse, and store as Parquet:
    python pipeline.py --from-date 2024-01-01 --to-date 2024-01-31

    # Only ingest already-downloaded CSVs (skip download):
    python pipeline.py --ingest-only

    # Show stats about existing Parquet data:
    python pipeline.py --stats-only

    # Download a single test date (good for verifying setup):
    python pipeline.py --from-date 2024-07-15 --to-date 2024-07-15
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).parent))

from config import RAW_DIR, PARQUET_DIR
from data.downloader import download_date_range
from data.parquet_store import ingest_bhavcopies, get_parquet_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pipeline")


def main():
    parser = argparse.ArgumentParser(
        description="Options Backtester — Data Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--from-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        help="Start date for download (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--to-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        help="End date for download (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--ingest-only",
        action="store_true",
        help="Skip download, only parse and ingest existing CSVs",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show Parquet store statistics",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Delay between NSE downloads in seconds (default: 1.5)",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Symbols to process (default: all — BANKNIFTY NIFTY FINNIFTY)",
    )

    args = parser.parse_args()

    # Stats only mode
    if args.stats_only:
        stats = get_parquet_stats()
        print(f"\n{'='*60}")
        print("Parquet Data Store Statistics")
        print(f"{'='*60}")
        print(json.dumps(stats, indent=2, default=str))
        return

    # Download + Ingest
    if not args.ingest_only:
        if not args.from_date or not args.to_date:
            parser.error("--from-date and --to-date are required unless using --ingest-only or --stats-only")

        logger.info("="*60)
        logger.info("STEP 1: Downloading bhavcopies from NSE")
        logger.info("="*60)
        logger.info("Date range: %s to %s", args.from_date, args.to_date)

        results = download_date_range(
            from_date=args.from_date,
            to_date=args.to_date,
            delay_seconds=args.delay,
        )

        success = sum(1 for v in results.values() if v is not None)
        failed = sum(1 for v in results.values() if v is None)
        logger.info("Download complete: %d successful, %d failed/holiday", success, failed)

    # Ingest CSVs into Parquet
    logger.info("="*60)
    logger.info("STEP 2: Ingesting CSVs into Parquet store")
    logger.info("="*60)

    stats = ingest_bhavcopies(RAW_DIR, symbols=args.symbols)

    print(f"\n{'='*60}")
    print("Pipeline Complete — Parquet Store Statistics")
    print(f"{'='*60}")
    print(json.dumps(stats, indent=2, default=str))

    # Summary table
    print(f"\n{'─'*60}")
    print(f"{'Category':<12} {'Symbol':<14} {'Rows':>10} {'Size (MB)':>10} {'Date Range'}")
    print(f"{'─'*60}")
    for category in ["options", "underlying"]:
        for symbol, info in stats.get(category, {}).items():
            date_range = f"{info.get('min_date', 'N/A')} → {info.get('max_date', 'N/A')}"
            print(
                f"{category:<12} {symbol:<14} {info['total_rows']:>10,} "
                f"{info['total_mb']:>10.2f} {date_range}"
            )
    print(f"{'─'*60}")


if __name__ == "__main__":
    main()
