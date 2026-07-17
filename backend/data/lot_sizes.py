"""
Historical lot size lookup for Indian index derivatives.

Lot sizes change periodically per NSE/SEBI circulars. This module provides
a date-aware lookup so the backtest engine always uses the correct lot size.

Sources: NSE circulars, broker documentation (Zerodha, Groww, Bajaj).
"""

from datetime import date
from bisect import bisect_right

# ── Lot Size Tables ────────────────────────────────────────────────────────────
# Each entry: (effective_from_date, lot_size)
# Sorted chronologically. The lot size is valid from that date until the next
# entry's date (exclusive).

BANKNIFTY_LOT_SIZES: list[tuple[date, int]] = [
    (date(2017, 1, 1), 40),     # ~40 from early days
    (date(2019, 10, 1), 20),    # SEBI revision
    (date(2020, 10, 29), 25),   # SEBI revision
    (date(2023, 7, 21), 15),    # Major reduction per SEBI
    (date(2024, 11, 20), 30),   # Increased per SEBI min contract value rules
    (date(2025, 7, 1), 35),     # Periodic review increase
    (date(2025, 10, 28), 30),   # Reduced back
]

NIFTY_LOT_SIZES: list[tuple[date, int]] = [
    (date(2017, 1, 1), 75),     # Historical default
    (date(2021, 4, 1), 50),     # Reduced
    (date(2024, 11, 20), 75),   # Increased per SEBI min contract value
    (date(2025, 10, 28), 65),   # Periodic review reduction
]

FINNIFTY_LOT_SIZES: list[tuple[date, int]] = [
    (date(2021, 1, 1), 40),     # Launch lot size
    (date(2024, 4, 26), 25),    # Reduced
    (date(2024, 11, 20), 65),   # Increased per SEBI
    (date(2026, 1, 1), 60),     # Periodic review
]

MIDCPNIFTY_LOT_SIZES: list[tuple[date, int]] = [
    (date(2022, 4, 1), 75),     # Launch lot size
    (date(2023, 4, 1), 50),     # Reduced
    (date(2024, 11, 20), 125),  # Increased per SEBI
    (date(2025, 10, 28), 100),  # Periodic review
]

# Master registry keyed by symbol
_LOT_SIZE_TABLES: dict[str, list[tuple[date, int]]] = {
    "BANKNIFTY": BANKNIFTY_LOT_SIZES,
    "NIFTY": NIFTY_LOT_SIZES,
    "FINNIFTY": FINNIFTY_LOT_SIZES,
    "MIDCPNIFTY": MIDCPNIFTY_LOT_SIZES,
}


def get_lot_size(symbol: str, trade_date: date) -> int:
    """
    Return the lot size for a given symbol on a given date.

    Uses binary search on the sorted effective-date table. Returns the lot size
    from the most recent effective date that is <= trade_date.

    Args:
        symbol: Index symbol (e.g. "BANKNIFTY", "NIFTY", "FINNIFTY").
        trade_date: The trading date to look up.

    Returns:
        The lot size (number of units per lot) effective on that date.

    Raises:
        ValueError: If the symbol is unknown or the date is before the earliest
                    entry in the table.
    """
    table = _LOT_SIZE_TABLES.get(symbol.upper())
    if table is None:
        raise ValueError(
            f"Unknown symbol '{symbol}'. "
            f"Available: {sorted(_LOT_SIZE_TABLES.keys())}"
        )

    # Extract just the dates for binary search
    effective_dates = [entry[0] for entry in table]

    # bisect_right gives us the index AFTER the last date <= trade_date
    idx = bisect_right(effective_dates, trade_date)

    if idx == 0:
        raise ValueError(
            f"No lot size data for {symbol} before {table[0][0]}. "
            f"Requested date: {trade_date}"
        )

    return table[idx - 1][1]


def get_lot_size_history(symbol: str) -> list[tuple[date, int]]:
    """Return the full lot size history for a symbol."""
    table = _LOT_SIZE_TABLES.get(symbol.upper())
    if table is None:
        raise ValueError(
            f"Unknown symbol '{symbol}'. "
            f"Available: {sorted(_LOT_SIZE_TABLES.keys())}"
        )
    return list(table)
