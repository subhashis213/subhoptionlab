"""
NSE F&O Bhavcopy CSV Parser.

Parses raw bhavcopy CSV files (both legacy and UDiFF formats) into clean,
normalized Polars DataFrames. Separates option contracts from futures/underlying
data.

── Legacy CSV columns (pre-July 8, 2024) ──
INSTRUMENT, SYMBOL, EXPIRY_DT, STRIKE_PR, OPTION_TYP, OPEN, HIGH, LOW, CLOSE,
SETTLE_PR, CONTRACTS, VAL_INLAKH, OPEN_INT, CHG_IN_OI, TIMESTAMP

── UDiFF CSV columns (post-July 8, 2024) ──
The new format has different column names that we normalize to a unified schema.
"""

import logging
from datetime import date, datetime
from pathlib import Path

import polars as pl

from config import SYMBOLS

logger = logging.getLogger(__name__)

# ── Unified Schema ─────────────────────────────────────────────────────────────
# All parsed data is normalized to these columns.

OPTIONS_SCHEMA = {
    "symbol": pl.Utf8,
    "expiry_date": pl.Date,
    "strike": pl.Float64,
    "option_type": pl.Utf8,       # CE or PE
    "open": pl.Float64,
    "high": pl.Float64,
    "low": pl.Float64,
    "close": pl.Float64,
    "settle_price": pl.Float64,
    "volume": pl.Int64,           # Number of contracts traded
    "oi": pl.Int64,               # Open interest
    "oi_change": pl.Int64,        # Change in OI
    "trade_date": pl.Date,
}

UNDERLYING_SCHEMA = {
    "symbol": pl.Utf8,
    "instrument_type": pl.Utf8,   # FUTIDX or OPTIDX (for futures underlying)
    "expiry_date": pl.Date,
    "open": pl.Float64,
    "high": pl.Float64,
    "low": pl.Float64,
    "close": pl.Float64,
    "settle_price": pl.Float64,
    "volume": pl.Int64,
    "oi": pl.Int64,
    "trade_date": pl.Date,
}


# ── Date Detection ─────────────────────────────────────────────────────────────

def _detect_format_from_filename(filepath: Path) -> str:
    """Detect whether a file is legacy or UDiFF format based on filename."""
    name = filepath.name
    if name.startswith("fo") and "bhav" in name.lower():
        return "legacy"
    elif name.startswith("BhavCopy_NSE_FO"):
        return "udiff"
    else:
        raise ValueError(f"Unrecognized bhavcopy filename format: {name}")


def _extract_date_from_filename(filepath: Path) -> date:
    """Extract the trading date from the bhavcopy filename."""
    name = filepath.name
    fmt = _detect_format_from_filename(filepath)

    if fmt == "legacy":
        # fo03OCT2023bhav.csv → "03OCT2023"
        date_part = name[2:11]
        return datetime.strptime(date_part, "%d%b%Y").date()
    else:
        # BhavCopy_NSE_FO_0_0_0_20240708_F_0000.csv → "20240708"
        parts = name.split("_")
        date_str = parts[6]
        return datetime.strptime(date_str, "%Y%m%d").date()


# ── Legacy Format Parser ──────────────────────────────────────────────────────


def _parse_legacy_csv(filepath: Path) -> pl.DataFrame:
    """
    Parse a legacy-format bhavcopy CSV.

    Columns: INSTRUMENT, SYMBOL, EXPIRY_DT, STRIKE_PR, OPTION_TYP, OPEN,
    HIGH, LOW, CLOSE, SETTLE_PR, CONTRACTS, VAL_INLAKH, OPEN_INT, CHG_IN_OI,
    TIMESTAMP
    """
    try:
        df = pl.read_csv(
            filepath,
            ignore_errors=True,
            truncate_ragged_lines=True,
        )
    except Exception as e:
        logger.error("Failed to read CSV %s: %s", filepath.name, e)
        return pl.DataFrame()

    # Strip whitespace from column names (NSE CSVs sometimes have trailing spaces)
    df = df.rename({col: col.strip() for col in df.columns})

    # Also strip whitespace from string columns
    for col in df.columns:
        if df[col].dtype == pl.Utf8:
            df = df.with_columns(pl.col(col).str.strip_chars().alias(col))

    # Check required columns exist
    required = {"INSTRUMENT", "SYMBOL", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP",
                "OPEN", "HIGH", "LOW", "CLOSE", "SETTLE_PR", "CONTRACTS",
                "OPEN_INT", "CHG_IN_OI", "TIMESTAMP"}
    missing = required - set(df.columns)
    if missing:
        logger.error("Missing columns in %s: %s", filepath.name, missing)
        return pl.DataFrame()

    return df


def _extract_options_legacy(df: pl.DataFrame, trade_date: date) -> pl.DataFrame:
    """Extract option contract rows from legacy-format DataFrame."""
    if df.is_empty():
        return pl.DataFrame(schema=OPTIONS_SCHEMA)

    options_df = df.filter(
        (pl.col("INSTRUMENT") == "OPTIDX") &
        (pl.col("SYMBOL").is_in(SYMBOLS)) &
        (pl.col("OPTION_TYP").is_in(["CE", "PE"]))
    )

    if options_df.is_empty():
        return pl.DataFrame(schema=OPTIONS_SCHEMA)

    return options_df.select([
        pl.col("SYMBOL").alias("symbol"),
        pl.col("EXPIRY_DT").str.strptime(pl.Date, "%d-%b-%Y").alias("expiry_date"),
        pl.col("STRIKE_PR").cast(pl.Float64).alias("strike"),
        pl.col("OPTION_TYP").alias("option_type"),
        pl.col("OPEN").cast(pl.Float64).alias("open"),
        pl.col("HIGH").cast(pl.Float64).alias("high"),
        pl.col("LOW").cast(pl.Float64).alias("low"),
        pl.col("CLOSE").cast(pl.Float64).alias("close"),
        pl.col("SETTLE_PR").cast(pl.Float64).alias("settle_price"),
        pl.col("CONTRACTS").cast(pl.Int64).alias("volume"),
        pl.col("OPEN_INT").cast(pl.Int64).alias("oi"),
        pl.col("CHG_IN_OI").cast(pl.Int64).alias("oi_change"),
        pl.lit(trade_date).alias("trade_date"),
    ])


def _extract_futures_legacy(df: pl.DataFrame, trade_date: date) -> pl.DataFrame:
    """Extract index futures rows (used as underlying proxy) from legacy format."""
    if df.is_empty():
        return pl.DataFrame(schema=UNDERLYING_SCHEMA)

    futures_df = df.filter(
        (pl.col("INSTRUMENT") == "FUTIDX") &
        (pl.col("SYMBOL").is_in(SYMBOLS))
    )

    if futures_df.is_empty():
        return pl.DataFrame(schema=UNDERLYING_SCHEMA)

    return futures_df.select([
        pl.col("SYMBOL").alias("symbol"),
        pl.col("INSTRUMENT").alias("instrument_type"),
        pl.col("EXPIRY_DT").str.strptime(pl.Date, "%d-%b-%Y").alias("expiry_date"),
        pl.col("OPEN").cast(pl.Float64).alias("open"),
        pl.col("HIGH").cast(pl.Float64).alias("high"),
        pl.col("LOW").cast(pl.Float64).alias("low"),
        pl.col("CLOSE").cast(pl.Float64).alias("close"),
        pl.col("SETTLE_PR").cast(pl.Float64).alias("settle_price"),
        pl.col("CONTRACTS").cast(pl.Int64).alias("volume"),
        pl.col("OPEN_INT").cast(pl.Int64).alias("oi"),
        pl.lit(trade_date).alias("trade_date"),
    ])


# ── UDiFF Format Parser ───────────────────────────────────────────────────────


def _parse_udiff_csv(filepath: Path) -> pl.DataFrame:
    """
    Parse a UDiFF-format bhavcopy CSV.

    UDiFF CSVs have different column names. We detect and map them.
    Common UDiFF columns include:
    TckrSymb, TradDt, BizDt, Sgmt, Src, FinInstrmTp, FinInstrmId, ISIN,
    XpryDt, FinistrmActlXpryDt, StrkPric, OptnTp, FinInstrmNm,
    OpnPric, HghPric, LwPric, ClsPric, LastPric, PrvsClsgPric,
    UndrlygPric, SttlmPric, OpnIntrst, ChngInOpnIntrst, TtlTradgVol,
    TtlTrfVal, TtlNbOfTxsExctd, SsnId, NewBrdLotQty, Rmks, Rsvd01-04
    """
    try:
        df = pl.read_csv(
            filepath,
            ignore_errors=True,
            truncate_ragged_lines=True,
        )
    except Exception as e:
        logger.error("Failed to read CSV %s: %s", filepath.name, e)
        return pl.DataFrame()

    # Strip whitespace from column names
    df = df.rename({col: col.strip() for col in df.columns})

    # Strip string columns
    for col in df.columns:
        if df[col].dtype == pl.Utf8:
            df = df.with_columns(pl.col(col).str.strip_chars().alias(col))

    return df


def _extract_options_udiff(df: pl.DataFrame, trade_date: date) -> pl.DataFrame:
    """Extract option contract rows from UDiFF-format DataFrame."""
    if df.is_empty():
        return pl.DataFrame(schema=OPTIONS_SCHEMA)

    # In UDiFF, TckrSymb has the clean symbol name (e.g. "BANKNIFTY")
    # and FinInstrmTp = "IDO" for Index Derivative Options.
    # FinInstrmNm has the full contract name (e.g. "BANKNIFTY24JUL48000CE")

    # Prefer TckrSymb for symbol matching (clean), fall back to FinInstrmNm
    filter_col = None
    for candidate in ["TckrSymb", "FinInstrmNm"]:
        if candidate in df.columns:
            filter_col = candidate
            break

    if filter_col is None:
        logger.error("Cannot find symbol column in UDiFF CSV")
        return pl.DataFrame(schema=OPTIONS_SCHEMA)

    # Build symbol filter
    symbol_filter = (
        pl.col(filter_col).str.starts_with("BANKNIFTY") |
        pl.col(filter_col).str.starts_with("NIFTY") |
        pl.col(filter_col).str.starts_with("FINNIFTY")
    )

    # Use FinInstrmTp if available for precise filtering
    if "FinInstrmTp" in df.columns:
        options_df = df.filter(
            (pl.col("FinInstrmTp") == "IDO") &
            (pl.col("OptnTp").is_in(["CE", "PE"])) &
            symbol_filter
        )
    else:
        options_df = df.filter(
            (pl.col("OptnTp").is_in(["CE", "PE"])) &
            symbol_filter
        )

    if options_df.is_empty():
        return pl.DataFrame(schema=OPTIONS_SCHEMA)

    # Determine symbol from the instrument name
    symbol_expr = (
        pl.when(pl.col(filter_col).str.starts_with("BANKNIFTY"))
        .then(pl.lit("BANKNIFTY"))
        .when(pl.col(filter_col).str.starts_with("FINNIFTY"))
        .then(pl.lit("FINNIFTY"))
        .when(pl.col(filter_col).str.starts_with("NIFTY"))
        .then(pl.lit("NIFTY"))
        .otherwise(pl.lit("UNKNOWN"))
    )

    # Map UDiFF columns to our unified schema
    # Handle different possible date formats in XpryDt
    expiry_col = "XpryDt" if "XpryDt" in options_df.columns else "FinistrmActlXpryDt"

    result = options_df.select([
        symbol_expr.alias("symbol"),
        pl.col(expiry_col).str.strptime(pl.Date, "%Y-%m-%d").alias("expiry_date"),
        pl.col("StrkPric").cast(pl.Float64).alias("strike"),
        pl.col("OptnTp").alias("option_type"),
        pl.col("OpnPric").cast(pl.Float64).alias("open"),
        pl.col("HghPric").cast(pl.Float64).alias("high"),
        pl.col("LwPric").cast(pl.Float64).alias("low"),
        pl.col("ClsPric").cast(pl.Float64).alias("close"),
        pl.col("SttlmPric").cast(pl.Float64).alias("settle_price"),
        pl.col("TtlTradgVol").cast(pl.Int64).alias("volume"),
        pl.col("OpnIntrst").cast(pl.Int64).alias("oi"),
        pl.col("ChngInOpnIntrst").cast(pl.Int64).alias("oi_change"),
        pl.lit(trade_date).alias("trade_date"),
    ])

    return result


def _extract_futures_udiff(df: pl.DataFrame, trade_date: date) -> pl.DataFrame:
    """Extract index futures from UDiFF format."""
    if df.is_empty():
        return pl.DataFrame(schema=UNDERLYING_SCHEMA)

    filter_col = None
    for candidate in ["TckrSymb", "FinInstrmNm"]:
        if candidate in df.columns:
            filter_col = candidate
            break

    if filter_col is None:
        return pl.DataFrame(schema=UNDERLYING_SCHEMA)

    # Filter for index futures using FinInstrmTp = "IDF" (Index Derivatives Futures)
    # This is the most reliable identifier in UDiFF format
    if "FinInstrmTp" in df.columns:
        fut_filter = (
            (pl.col("FinInstrmTp") == "IDF") &
            (
                pl.col(filter_col).str.starts_with("BANKNIFTY") |
                pl.col(filter_col).str.starts_with("NIFTY") |
                pl.col(filter_col).str.starts_with("FINNIFTY")
            )
        )
    else:
        # Fallback: not CE/PE and no strike
        fut_filter = (
            (~pl.col("OptnTp").is_in(["CE", "PE"])) &
            (
                pl.col(filter_col).str.starts_with("BANKNIFTY") |
                pl.col(filter_col).str.starts_with("NIFTY") |
                pl.col(filter_col).str.starts_with("FINNIFTY")
            )
        )

    futures_df = df.filter(fut_filter)

    if futures_df.is_empty():
        return pl.DataFrame(schema=UNDERLYING_SCHEMA)

    symbol_expr = (
        pl.when(pl.col(filter_col).str.starts_with("BANKNIFTY"))
        .then(pl.lit("BANKNIFTY"))
        .when(pl.col(filter_col).str.starts_with("FINNIFTY"))
        .then(pl.lit("FINNIFTY"))
        .when(pl.col(filter_col).str.starts_with("NIFTY"))
        .then(pl.lit("NIFTY"))
        .otherwise(pl.lit("UNKNOWN"))
    )

    expiry_col = "XpryDt" if "XpryDt" in futures_df.columns else "FinistrmActlXpryDt"

    return futures_df.select([
        symbol_expr.alias("symbol"),
        pl.lit("FUTIDX").alias("instrument_type"),
        pl.col(expiry_col).str.strptime(pl.Date, "%Y-%m-%d").alias("expiry_date"),
        pl.col("OpnPric").cast(pl.Float64).alias("open"),
        pl.col("HghPric").cast(pl.Float64).alias("high"),
        pl.col("LwPric").cast(pl.Float64).alias("low"),
        pl.col("ClsPric").cast(pl.Float64).alias("close"),
        pl.col("SttlmPric").cast(pl.Float64).alias("settle_price"),
        pl.col("TtlTradgVol").cast(pl.Int64).alias("volume"),
        pl.col("OpnIntrst").cast(pl.Int64).alias("oi"),
        pl.lit(trade_date).alias("trade_date"),
    ])


# ── Public API ─────────────────────────────────────────────────────────────────


def parse_bhavcopy(filepath: Path) -> tuple[pl.DataFrame, pl.DataFrame]:
    """
    Parse a single bhavcopy CSV file into options and futures DataFrames.

    Automatically detects the file format (legacy vs UDiFF) from the filename.

    Args:
        filepath: Path to the CSV file.

    Returns:
        Tuple of (options_df, futures_df) with unified schemas.
    """
    fmt = _detect_format_from_filename(filepath)
    trade_date = _extract_date_from_filename(filepath)

    logger.debug("Parsing %s (%s format, date=%s)", filepath.name, fmt, trade_date)

    if fmt == "legacy":
        raw_df = _parse_legacy_csv(filepath)
        options_df = _extract_options_legacy(raw_df, trade_date)
        futures_df = _extract_futures_legacy(raw_df, trade_date)
    else:
        raw_df = _parse_udiff_csv(filepath)
        options_df = _extract_options_udiff(raw_df, trade_date)
        futures_df = _extract_futures_udiff(raw_df, trade_date)

    logger.info(
        "Parsed %s: %d option rows, %d futures rows",
        filepath.name,
        len(options_df),
        len(futures_df),
    )
    return options_df, futures_df


def parse_all_bhavcopies(
    raw_dir: Path,
    symbols: list[str] | None = None,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """
    Parse all bhavcopy CSVs in a directory and concatenate results.

    Args:
        raw_dir: Directory containing raw CSV files.
        symbols: Optional filter — only include these symbols.

    Returns:
        Tuple of (all_options_df, all_futures_df).
    """
    if symbols is None:
        symbols = SYMBOLS

    all_options: list[pl.DataFrame] = []
    all_futures: list[pl.DataFrame] = []

    csv_files = sorted(raw_dir.glob("*.csv"))
    logger.info("Found %d CSV files in %s", len(csv_files), raw_dir)

    for filepath in csv_files:
        try:
            options_df, futures_df = parse_bhavcopy(filepath)

            if not options_df.is_empty():
                # Filter to requested symbols
                options_df = options_df.filter(pl.col("symbol").is_in(symbols))
                all_options.append(options_df)

            if not futures_df.is_empty():
                futures_df = futures_df.filter(pl.col("symbol").is_in(symbols))
                all_futures.append(futures_df)

        except Exception as e:
            logger.error("Error parsing %s: %s", filepath.name, e)
            continue

    # Concatenate all results
    combined_options = (
        pl.concat(all_options) if all_options
        else pl.DataFrame(schema=OPTIONS_SCHEMA)
    )
    combined_futures = (
        pl.concat(all_futures) if all_futures
        else pl.DataFrame(schema=UNDERLYING_SCHEMA)
    )

    logger.info(
        "Total parsed: %d option rows, %d futures rows across %d files",
        len(combined_options),
        len(combined_futures),
        len(csv_files),
    )

    return combined_options, combined_futures
