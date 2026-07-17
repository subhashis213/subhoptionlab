"""
DuckDB Query Module.

Provides the public interface for the backtest engine to query historical
option and underlying prices from the Parquet data store.

All queries run against partitioned Parquet files via DuckDB — no full
datasets are loaded into memory. DuckDB pushes down filters to the file
scan level, so only relevant rows are read.

Extension point: When minute-level data is added later, these functions
gain an optional `time` parameter without changing their public signatures.
"""

import logging
from datetime import date
from pathlib import Path

import duckdb

from config import PARQUET_DIR, STRIKE_INTERVALS

logger = logging.getLogger(__name__)


def _get_connection(parquet_dir: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Create a DuckDB connection (in-memory, reads from Parquet on disk)."""
    return duckdb.connect(database=":memory:")


def _options_glob(symbol: str, parquet_dir: Path | None = None) -> str:
    """Return the glob pattern for a symbol's options Parquet files."""
    base = parquet_dir or PARQUET_DIR
    return str(base / "options" / symbol / "*.parquet")


def _underlying_glob(symbol: str, parquet_dir: Path | None = None) -> str:
    """Return the glob pattern for a symbol's underlying Parquet files."""
    base = parquet_dir or PARQUET_DIR
    return str(base / "underlying" / symbol / "*.parquet")


# ── Option Price Queries ───────────────────────────────────────────────────────


def get_option_price(
    symbol: str,
    strike: float,
    option_type: str,
    expiry: date,
    trade_date: date,
    parquet_dir: Path | None = None,
) -> dict | None:
    """
    Get OHLC data for a specific option contract on a specific date.

    Args:
        symbol: Index symbol (BANKNIFTY, NIFTY, FINNIFTY).
        strike: Strike price (e.g. 48000.0).
        option_type: "CE" or "PE".
        expiry: Expiry date of the contract.
        trade_date: The trading date to look up.
        parquet_dir: Override parquet directory.

    Returns:
        Dict with {open, high, low, close, settle_price, oi, volume}
        or None if no data found.
    """
    glob_pattern = _options_glob(symbol, parquet_dir)
    con = _get_connection()

    try:
        result = con.execute(
            """
            SELECT open, high, low, close, settle_price, oi, volume
            FROM read_parquet(?)
            WHERE strike = ?
              AND option_type = ?
              AND expiry_date = ?
              AND trade_date = ?
            LIMIT 1
            """,
            [glob_pattern, strike, option_type, expiry, trade_date],
        ).fetchone()

        if result is None:
            logger.debug(
                "No option data: %s %s %s expiry=%s date=%s",
                symbol, strike, option_type, expiry, trade_date,
            )
            return None

        return {
            "open": result[0],
            "high": result[1],
            "low": result[2],
            "close": result[3],
            "settle_price": result[4],
            "oi": result[5],
            "volume": result[6],
        }
    except Exception as e:
        logger.error("Error querying option price: %s", e)
        return None
    finally:
        con.close()


def get_option_chain(
    symbol: str,
    expiry: date,
    trade_date: date,
    parquet_dir: Path | None = None,
) -> list[dict]:
    """
    Get the full option chain for a symbol/expiry/date.

    Returns:
        List of dicts, one per strike/type combination.
    """
    glob_pattern = _options_glob(symbol, parquet_dir)
    con = _get_connection()

    try:
        results = con.execute(
            """
            SELECT strike, option_type, open, high, low, close, settle_price, oi, volume
            FROM read_parquet(?)
            WHERE expiry_date = ?
              AND trade_date = ?
            ORDER BY strike, option_type
            """,
            [glob_pattern, expiry, trade_date],
        ).fetchall()

        return [
            {
                "strike": row[0],
                "option_type": row[1],
                "open": row[2],
                "high": row[3],
                "low": row[4],
                "close": row[5],
                "settle_price": row[6],
                "oi": row[7],
                "volume": row[8],
            }
            for row in results
        ]
    except Exception as e:
        logger.error("Error querying option chain: %s", e)
        return []
    finally:
        con.close()


# ── Underlying Price Queries ───────────────────────────────────────────────────


def get_underlying_price(
    symbol: str,
    trade_date: date,
    use_futures: bool = False,
    parquet_dir: Path | None = None,
) -> float | None:
    """
    Get the underlying price for a symbol on a given date.

    With daily data, we use the futures close price from the bhavcopy.
    The "spot" price is approximated by the nearest-month futures close
    (closest proxy available from bhavcopy data).

    When use_futures=True, we explicitly use the current-month futures price.
    When use_futures=False, we still use futures close as our best proxy
    for spot (bhavcopy doesn't contain actual index spot values — we'd need
    a separate source for that).

    Args:
        symbol: Index symbol.
        trade_date: The trading date.
        use_futures: If True, use futures. If False, use nearest-month futures
                     as spot proxy.
        parquet_dir: Override parquet directory.

    Returns:
        The close price, or None if no data found.
    """
    glob_pattern = _underlying_glob(symbol, parquet_dir)
    con = _get_connection()

    try:
        # Get the nearest-month futures contract (closest expiry >= trade_date)
        result = con.execute(
            """
            SELECT close, expiry_date
            FROM read_parquet(?)
            WHERE trade_date = ?
            ORDER BY expiry_date ASC
            LIMIT 1
            """,
            [glob_pattern, trade_date],
        ).fetchone()

        if result is None:
            logger.debug("No underlying data: %s date=%s", symbol, trade_date)
            return None

        return float(result[0])

    except Exception as e:
        logger.error("Error querying underlying price: %s", e)
        return None
    finally:
        con.close()


# ── Strike Resolution ──────────────────────────────────────────────────────────


def resolve_atm_strike(symbol: str, price: float) -> int:
    """
    Round a price to the nearest valid ATM strike for a given symbol.

    BANKNIFTY: 100-point intervals (e.g. 48000, 48100, 48200)
    NIFTY: 50-point intervals (e.g. 24000, 24050, 24100)
    FINNIFTY: 50-point intervals

    Args:
        symbol: Index symbol.
        price: The spot/futures price to round.

    Returns:
        The nearest valid strike price as an integer.
    """
    interval = STRIKE_INTERVALS.get(symbol.upper())
    if interval is None:
        raise ValueError(
            f"Unknown symbol '{symbol}'. "
            f"Available: {sorted(STRIKE_INTERVALS.keys())}"
        )

    return round(price / interval) * interval


# ── Expiry Resolution ──────────────────────────────────────────────────────────


def resolve_expiry(
    symbol: str,
    trade_date: date,
    mode: str = "same_day",
    parquet_dir: Path | None = None,
) -> date | None:
    """
    Find the appropriate weekly expiry for a trading date.

    'same_day' mode: Returns the current week's expiry. If trade_date IS
    the expiry day, returns trade_date itself.

    'next_day' mode: Returns the NEXT week's expiry after the current one.

    This works by querying actual expiry dates from the Parquet data, so
    it correctly handles expiry day changes, special expiries, etc.

    Args:
        symbol: Index symbol.
        trade_date: The trading date to find expiry for.
        mode: "same_day" or "next_day".
        parquet_dir: Override parquet directory.

    Returns:
        The expiry date, or None if no data found.
    """
    glob_pattern = _options_glob(symbol, parquet_dir)
    con = _get_connection()

    try:
        if mode == "same_day":
            # Find the nearest expiry >= trade_date
            result = con.execute(
                """
                SELECT DISTINCT expiry_date
                FROM read_parquet(?)
                WHERE trade_date = ?
                  AND expiry_date >= ?
                ORDER BY expiry_date ASC
                LIMIT 1
                """,
                [glob_pattern, trade_date, trade_date],
            ).fetchone()
        elif mode == "next_day":
            # Find the second nearest expiry >= trade_date
            result = con.execute(
                """
                SELECT DISTINCT expiry_date
                FROM read_parquet(?)
                WHERE trade_date = ?
                  AND expiry_date >= ?
                ORDER BY expiry_date ASC
                LIMIT 1 OFFSET 1
                """,
                [glob_pattern, trade_date, trade_date],
            ).fetchone()
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'same_day' or 'next_day'.")

        if result is None:
            logger.debug("No expiry found: %s date=%s mode=%s", symbol, trade_date, mode)
            return None

        return result[0]

    except Exception as e:
        logger.error("Error resolving expiry: %s", e)
        return None
    finally:
        con.close()


def get_available_expiries(
    symbol: str,
    date_from: date | None = None,
    date_to: date | None = None,
    parquet_dir: Path | None = None,
) -> list[date]:
    """
    List all distinct expiry dates for a symbol within an optional date range.

    Args:
        symbol: Index symbol.
        date_from: Optional start of range (filters by expiry_date).
        date_to: Optional end of range.
        parquet_dir: Override parquet directory.

    Returns:
        Sorted list of expiry dates.
    """
    glob_pattern = _options_glob(symbol, parquet_dir)
    con = _get_connection()

    try:
        query = "SELECT DISTINCT expiry_date FROM read_parquet(?)"
        params: list = [glob_pattern]
        conditions = []

        if date_from is not None:
            conditions.append("expiry_date >= ?")
            params.append(date_from)

        if date_to is not None:
            conditions.append("expiry_date <= ?")
            params.append(date_to)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY expiry_date ASC"

        results = con.execute(query, params).fetchall()
        return [row[0] for row in results]

    except Exception as e:
        logger.error("Error getting expiries: %s", e)
        return []
    finally:
        con.close()


def get_available_trade_dates(
    symbol: str,
    date_from: date | None = None,
    date_to: date | None = None,
    parquet_dir: Path | None = None,
) -> list[date]:
    """
    List all distinct trading dates available in the data for a symbol.

    This is the ground truth for "what dates do we have data for?"

    Args:
        symbol: Index symbol.
        date_from: Optional start of range.
        date_to: Optional end of range.
        parquet_dir: Override parquet directory.

    Returns:
        Sorted list of trading dates.
    """
    glob_pattern = _options_glob(symbol, parquet_dir)
    con = _get_connection()

    try:
        query = "SELECT DISTINCT trade_date FROM read_parquet(?)"
        params: list = [glob_pattern]
        conditions = []

        if date_from is not None:
            conditions.append("trade_date >= ?")
            params.append(date_from)

        if date_to is not None:
            conditions.append("trade_date <= ?")
            params.append(date_to)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY trade_date ASC"

        results = con.execute(query, params).fetchall()
        return [row[0] for row in results]

    except Exception as e:
        logger.error("Error getting trade dates: %s", e)
        return []
    finally:
        con.close()


def get_available_strikes(
    symbol: str,
    expiry: date,
    trade_date: date,
    option_type: str | None = None,
    parquet_dir: Path | None = None,
) -> list[float]:
    """
    List all available strikes for a symbol/expiry/date.

    Args:
        symbol: Index symbol.
        expiry: Expiry date.
        trade_date: Trading date.
        option_type: Optional filter ("CE" or "PE").
        parquet_dir: Override parquet directory.

    Returns:
        Sorted list of available strike prices.
    """
    glob_pattern = _options_glob(symbol, parquet_dir)
    con = _get_connection()

    try:
        query = """
            SELECT DISTINCT strike
            FROM read_parquet(?)
            WHERE expiry_date = ? AND trade_date = ?
        """
        params: list = [glob_pattern, expiry, trade_date]

        if option_type is not None:
            query += " AND option_type = ?"
            params.append(option_type)

        query += " ORDER BY strike ASC"

        results = con.execute(query, params).fetchall()
        return [row[0] for row in results]

    except Exception as e:
        logger.error("Error getting strikes: %s", e)
        return []
    finally:
        con.close()
