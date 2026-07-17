"""
Expiry Resolver — finds the correct weekly expiry for a trading date.

Handles historical changes in expiry days:
- BANKNIFTY: Wednesday (until Apr 2024), then Tuesday
- NIFTY: Thursday
- FINNIFTY: Tuesday (discontinued Nov 2024)

Wraps the DuckDB query layer's resolve_expiry with additional logic.
"""

from datetime import date
from pathlib import Path

from data.queries import resolve_expiry as _query_resolve_expiry
from data.queries import get_available_expiries as _query_get_expiries


def resolve_expiry(
    symbol: str,
    trade_date: date,
    mode: str = "same_day",
    parquet_dir: Path | None = None,
) -> date | None:
    """
    Find the appropriate weekly expiry for a trading date.

    This delegates to the DuckDB query layer, which uses actual expiry dates
    from the data. This is the most reliable method since it handles:
    - Expiry day changes (BANKNIFTY Wed→Tue)
    - Holiday-shifted expiries
    - Monthly vs weekly expiries
    - Discontinued contracts (FINNIFTY)

    Args:
        symbol: Index symbol.
        trade_date: The trading date.
        mode: "same_day" = current/nearest expiry, "next_day" = next week's.
        parquet_dir: Override parquet directory.

    Returns:
        The expiry date, or None if not found.
    """
    return _query_resolve_expiry(symbol, trade_date, mode, parquet_dir)


def get_weekly_expiry_day(symbol: str, trade_date: date) -> int:
    """
    Return the expected weekly expiry weekday for a symbol on a given date.

    Returns weekday as integer (0=Monday, ..., 6=Sunday).

    This is used as a fallback/heuristic when data-driven resolution
    isn't available.
    """
    symbol = symbol.upper()

    if symbol == "BANKNIFTY":
        # BANKNIFTY switched from Wednesday to Tuesday around April 2024
        if trade_date >= date(2024, 4, 1):
            return 1  # Tuesday
        else:
            return 2  # Wednesday

    elif symbol == "NIFTY":
        return 3  # Thursday

    elif symbol == "FINNIFTY":
        return 1  # Tuesday (discontinued Nov 2024, but always was Tuesday)

    else:
        raise ValueError(f"Unknown symbol: {symbol}")
