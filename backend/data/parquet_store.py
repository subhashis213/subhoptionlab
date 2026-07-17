"""
Parquet File Store.

Converts parsed DataFrames into partitioned Parquet files for efficient
querying by DuckDB. Partitioned by symbol and year for fast range scans.

Directory structure:
  parquet_data/
  ├── options/
  │   ├── BANKNIFTY/
  │   │   ├── 2017.parquet
  │   │   ├── 2018.parquet
  │   │   └── ...
  │   ├── NIFTY/
  │   │   └── ...
  │   └── FINNIFTY/
  │       └── ...
  └── underlying/
      ├── BANKNIFTY/
      │   ├── 2017.parquet
      │   └── ...
      └── NIFTY/
          └── ...
"""

import logging
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from config import PARQUET_DIR

logger = logging.getLogger(__name__)


def _ensure_dir(path: Path) -> None:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


def write_options_parquet(
    options_df: pl.DataFrame,
    output_dir: Path | None = None,
) -> dict[str, list[Path]]:
    """
    Write options data to partitioned Parquet files.

    Partitions by symbol/year. Appends to existing files by reading, deduplicating,
    and rewriting (Parquet doesn't support append natively).

    Args:
        options_df: DataFrame with the unified options schema.
        output_dir: Base directory for parquet output. Defaults to PARQUET_DIR.

    Returns:
        Dict mapping symbol to list of written Parquet file paths.
    """
    if output_dir is None:
        output_dir = PARQUET_DIR

    if options_df.is_empty():
        logger.warning("No options data to write")
        return {}

    options_base = output_dir / "options"
    _ensure_dir(options_base)

    written_files: dict[str, list[Path]] = {}

    # Extract year from trade_date for partitioning
    df_with_year = options_df.with_columns(
        pl.col("trade_date").dt.year().alias("_year")
    )

    # Group by symbol and year
    for (symbol, year), group_df in df_with_year.group_by(["symbol", "_year"]):
        symbol_dir = options_base / str(symbol)
        _ensure_dir(symbol_dir)

        parquet_path = symbol_dir / f"{year}.parquet"
        group_data = group_df.drop("_year")

        if parquet_path.exists():
            # Read existing data and merge
            existing_df = pl.read_parquet(parquet_path)
            combined = pl.concat([existing_df, group_data])

            # Deduplicate on (trade_date, expiry_date, strike, option_type)
            combined = combined.unique(
                subset=["trade_date", "expiry_date", "strike", "option_type"],
                keep="last",
            )
            combined = combined.sort(["trade_date", "expiry_date", "strike", "option_type"])
        else:
            combined = group_data.sort(["trade_date", "expiry_date", "strike", "option_type"])

        # Write to parquet
        combined.write_parquet(parquet_path, compression="snappy")

        written_files.setdefault(str(symbol), []).append(parquet_path)
        logger.info(
            "Wrote %s: %d rows → %s",
            symbol, len(combined), parquet_path,
        )

    return written_files


def write_underlying_parquet(
    futures_df: pl.DataFrame,
    output_dir: Path | None = None,
) -> dict[str, list[Path]]:
    """
    Write underlying/futures data to partitioned Parquet files.

    Args:
        futures_df: DataFrame with the unified underlying/futures schema.
        output_dir: Base directory for parquet output. Defaults to PARQUET_DIR.

    Returns:
        Dict mapping symbol to list of written Parquet file paths.
    """
    if output_dir is None:
        output_dir = PARQUET_DIR

    if futures_df.is_empty():
        logger.warning("No underlying data to write")
        return {}

    underlying_base = output_dir / "underlying"
    _ensure_dir(underlying_base)

    written_files: dict[str, list[Path]] = {}

    df_with_year = futures_df.with_columns(
        pl.col("trade_date").dt.year().alias("_year")
    )

    for (symbol, year), group_df in df_with_year.group_by(["symbol", "_year"]):
        symbol_dir = underlying_base / str(symbol)
        _ensure_dir(symbol_dir)

        parquet_path = symbol_dir / f"{year}.parquet"
        group_data = group_df.drop("_year")

        if parquet_path.exists():
            existing_df = pl.read_parquet(parquet_path)
            combined = pl.concat([existing_df, group_data])
            combined = combined.unique(
                subset=["trade_date", "expiry_date"],
                keep="last",
            )
            combined = combined.sort(["trade_date", "expiry_date"])
        else:
            combined = group_data.sort(["trade_date", "expiry_date"])

        combined.write_parquet(parquet_path, compression="snappy")

        written_files.setdefault(str(symbol), []).append(parquet_path)
        logger.info(
            "Wrote %s underlying: %d rows → %s",
            symbol, len(combined), parquet_path,
        )

    return written_files


def get_parquet_stats(output_dir: Path | None = None) -> dict:
    """
    Get statistics about the Parquet data store.

    Returns:
        Dict with row counts, date ranges, and file sizes per symbol.
    """
    if output_dir is None:
        output_dir = PARQUET_DIR

    stats = {"options": {}, "underlying": {}}

    for category in ["options", "underlying"]:
        category_dir = output_dir / category
        if not category_dir.exists():
            continue

        for symbol_dir in sorted(category_dir.iterdir()):
            if not symbol_dir.is_dir():
                continue

            symbol = symbol_dir.name
            total_rows = 0
            total_bytes = 0
            min_date = None
            max_date = None

            for pq_file in sorted(symbol_dir.glob("*.parquet")):
                try:
                    df = pl.read_parquet(pq_file)
                    total_rows += len(df)
                    total_bytes += pq_file.stat().st_size

                    dates = df["trade_date"]
                    file_min = dates.min()
                    file_max = dates.max()

                    if min_date is None or file_min < min_date:
                        min_date = file_min
                    if max_date is None or file_max > max_date:
                        max_date = file_max
                except Exception as e:
                    logger.error("Error reading %s: %s", pq_file, e)

            stats[category][symbol] = {
                "total_rows": total_rows,
                "total_bytes": total_bytes,
                "total_mb": round(total_bytes / (1024 * 1024), 2),
                "min_date": str(min_date) if min_date else None,
                "max_date": str(max_date) if max_date else None,
            }

    return stats


# ── Pipeline: Parse + Store ────────────────────────────────────────────────────


def ingest_bhavcopies(
    raw_dir: Path,
    output_dir: Path | None = None,
    symbols: list[str] | None = None,
) -> dict:
    """
    Full pipeline: parse all bhavcopy CSVs and write to Parquet store.

    This is the main entry point for the data pipeline.

    Args:
        raw_dir: Directory containing raw bhavcopy CSV files.
        output_dir: Parquet output directory. Defaults to PARQUET_DIR.
        symbols: Optional symbol filter. Defaults to all configured symbols.

    Returns:
        Statistics about the ingested data.
    """
    from data.parser import parse_all_bhavcopies

    logger.info("Starting bhavcopy ingestion from %s", raw_dir)

    # Parse all CSVs
    options_df, futures_df = parse_all_bhavcopies(raw_dir, symbols)

    # Write to Parquet
    options_files = write_options_parquet(options_df, output_dir)
    underlying_files = write_underlying_parquet(futures_df, output_dir)

    # Get stats
    stats = get_parquet_stats(output_dir)

    logger.info("Ingestion complete. Stats: %s", stats)
    return stats


# ── CLI Entry Point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Ingest bhavcopy CSVs into Parquet store."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=None,
        help="Directory with raw CSV files (default: raw_bhavcopies/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Parquet output directory (default: backend/parquet_data/)",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only print stats, don't ingest.",
    )

    args = parser.parse_args()

    if args.stats_only:
        stats = get_parquet_stats(args.output_dir)
        print(json.dumps(stats, indent=2, default=str))
    else:
        from config import RAW_DIR
        raw = args.raw_dir or RAW_DIR
        stats = ingest_bhavcopies(raw, args.output_dir)
        print(f"\n{'='*60}")
        print("Ingestion Complete")
        print(f"{'='*60}")
        print(json.dumps(stats, indent=2, default=str))
