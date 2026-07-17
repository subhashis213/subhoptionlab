"""
Core Backtest Engine.

For each trading day in the date range:
1. Resolve the expiry, ATM strike, and each leg's strike + entry price
2. Simulate SL/target using daily High/Low as proxy (conservative)
3. Apply strategy-level SL/TP and profit protection
4. Close remaining legs at exit_time
5. Record {date, pnl, exit_reason, per_leg_breakdown}

With daily-only data, SL/target checks use the day's High/Low:
- For a SELL leg: if option High ≥ SL price → SL hit
- For a SELL leg: if option Low ≤ target price → target hit
- Vice versa for BUY legs
- When both could trigger same day, assume SL hit first (conservative)
"""

import logging
from datetime import date
from pathlib import Path

from data.queries import (
    get_option_price,
    get_underlying_price,
    resolve_atm_strike,
    resolve_expiry,
    get_available_trade_dates,
)
from data.lot_sizes import get_lot_size
from engine.schemas import (
    StrategyConfig,
    LegConfig,
    BacktestRequest,
    BacktestResult,
    DailyResult,
    LegResult,
    ExitReason,
)
from engine.strike_resolver import resolve_strike
from engine.minute_simulator import simulate_intraday_leg

logger = logging.getLogger(__name__)


def _calculate_sl_price(
    entry_price: float,
    sl_percent: float,
    action: str,
) -> float:
    """
    Calculate the stop loss trigger price.

    For SELL: SL is when price RISES by sl_percent from entry → loss for seller.
    For BUY: SL is when price FALLS by sl_percent from entry → loss for buyer.
    """
    if action == "SELL":
        return entry_price * (1 + sl_percent / 100)
    else:  # BUY
        return entry_price * (1 - sl_percent / 100)


def _calculate_target_price(
    entry_price: float,
    target_percent: float,
    action: str,
) -> float:
    """
    Calculate the target profit trigger price.

    For SELL: Target is when price FALLS by target_percent → profit for seller.
    For BUY: Target is when price RISES by target_percent → profit for buyer.
    """
    if action == "SELL":
        return entry_price * (1 - target_percent / 100)
    else:  # BUY
        return entry_price * (1 + target_percent / 100)


def _check_leg_sl_target(
    entry_price: float,
    day_high: float,
    day_low: float,
    action: str,
    sl_percent: float | None,
    target_percent: float | None,
    close_price: float,
) -> tuple[float, str]:
    """
    Check if a leg's SL or target was hit using daily OHLC proxy.

    Returns:
        (exit_price, exit_reason) where exit_reason is one of:
        "leg_sl_hit", "leg_target_hit", "time_exit"
    """
    sl_hit = False
    target_hit = False
    sl_exit_price = close_price
    target_exit_price = close_price

    if sl_percent is not None and sl_percent > 0:
        sl_price = _calculate_sl_price(entry_price, sl_percent, action)
        if action == "SELL":
            # For SELL, SL triggers when option price RISES above SL
            if day_high >= sl_price:
                sl_hit = True
                sl_exit_price = sl_price
        else:  # BUY
            # For BUY, SL triggers when option price FALLS below SL
            if day_low <= sl_price:
                sl_hit = True
                sl_exit_price = sl_price

    if target_percent is not None and target_percent > 0:
        target_price = _calculate_target_price(entry_price, target_percent, action)
        if action == "SELL":
            # For SELL, target hits when option price FALLS below target
            if day_low <= target_price:
                target_hit = True
                target_exit_price = target_price
        else:  # BUY
            # For BUY, target hits when option price RISES above target
            if day_high >= target_price:
                target_hit = True
                target_exit_price = target_price

    # If both could trigger, assume SL hit first (conservative)
    if sl_hit and target_hit:
        return sl_exit_price, "leg_sl_hit"
    elif sl_hit:
        return sl_exit_price, "leg_sl_hit"
    elif target_hit:
        return target_exit_price, "leg_target_hit"
    else:
        return close_price, "time_exit"


def _calculate_leg_pnl(
    entry_price: float,
    exit_price: float,
    action: str,
    lots: int,
    lot_size: int,
) -> tuple[float, float]:
    """
    Calculate P&L for a single leg.

    Returns:
        (pnl_points, pnl_value)
    """
    if action == "SELL":
        pnl_points = entry_price - exit_price
    else:  # BUY
        pnl_points = exit_price - entry_price

    pnl_value = pnl_points * lots * lot_size
    return pnl_points, pnl_value


def run_backtest(
    config: StrategyConfig,
    date_from: date,
    date_to: date,
    parquet_dir: Path | None = None,
) -> BacktestResult:
    """
    Run a full backtest for a strategy over a date range.

    Args:
        config: Strategy configuration.
        date_from: Start date (inclusive).
        date_to: End date (inclusive).
        parquet_dir: Override parquet data directory.

    Returns:
        BacktestResult with daily results and metrics placeholder.
    """
    symbol = config.symbol.upper()
    daily_results: list[DailyResult] = []

    # Get actual trading days from our data
    trade_dates = get_available_trade_dates(
        symbol, date_from, date_to, parquet_dir
    )

    if not trade_dates:
        logger.warning(
            "No trading data available for %s from %s to %s",
            symbol, date_from, date_to,
        )
        return BacktestResult(
            strategy=config,
            date_from=date_from,
            date_to=date_to,
            daily_results=[],
            total_trading_days=0,
        )

    logger.info(
        "Running backtest: %s, %d trading days (%s to %s), %d legs",
        symbol, len(trade_dates), trade_dates[0], trade_dates[-1],
        len(config.legs),
    )

    for trade_date in trade_dates:
        try:
            day_result = _process_trading_day(
                config, trade_date, symbol, parquet_dir
            )
            if day_result is not None:
                daily_results.append(day_result)
        except Exception as e:
            logger.error("Error processing %s: %s", trade_date, e)
            continue

    logger.info(
        "Backtest complete: %d days processed, total P&L = %.2f points",
        len(daily_results),
        sum(d.total_pnl_points for d in daily_results),
    )

    return BacktestResult(
        strategy=config,
        date_from=date_from,
        date_to=date_to,
        daily_results=daily_results,
        total_trading_days=len(daily_results),
    )


def _process_trading_day(
    config: StrategyConfig,
    trade_date: date,
    symbol: str,
    parquet_dir: Path | None,
) -> DailyResult | None:
    """Process a single trading day of the backtest."""

    # Step 1: Get underlying price for ATM calculation
    underlying_price = get_underlying_price(
        symbol, trade_date,
        use_futures=config.use_futures_for_atm,
        parquet_dir=parquet_dir,
    )
    if underlying_price is None:
        logger.debug("No underlying price for %s on %s, skipping", symbol, trade_date)
        return None

    # Step 2: Resolve ATM strike
    atm_strike = resolve_atm_strike(symbol, underlying_price)

    # Step 3: Resolve expiry
    expiry = resolve_expiry(
        symbol, trade_date, config.expiry_mode.value, parquet_dir
    )
    if expiry is None:
        logger.debug("No expiry found for %s on %s, skipping", symbol, trade_date)
        return None

    # Step 4: Get lot size
    lot_size = get_lot_size(symbol, trade_date)

    # Step 5: Process each leg
    leg_results: list[LegResult] = []
    total_pnl_points = 0.0
    total_pnl_value = 0.0
    day_exit_reason = "time_exit"

    for leg_config in config.legs:
        leg_result = _process_leg(
            leg_config, atm_strike, expiry, trade_date,
            symbol, lot_size, parquet_dir,
            entry_time=config.entry_time,
            exit_time=config.exit_time,
        )
        if leg_result is None:
            continue

        leg_results.append(leg_result)
        total_pnl_points += leg_result.pnl_points * leg_result.lots
        total_pnl_value += leg_result.pnl_value

    if not leg_results:
        return None

    # Determine descriptive day exit reason based on which legs hit SL/TP vs time exit
    sl_legs = [l.option_type for l in leg_results if l.exit_reason == "leg_sl_hit"]
    tp_legs = [l.option_type for l in leg_results if l.exit_reason == "leg_target_hit"]

    if len(sl_legs) > 1:
        day_exit_reason = f"{' & '.join(sl_legs)} SL HIT (DOUBLE SL)"
    elif len(sl_legs) == 1:
        other_reason = "Time Exit" if not tp_legs else f"{tp_legs[0]} Target Hit"
        day_exit_reason = f"{sl_legs[0]} SL HIT ({other_reason})"
    elif len(tp_legs) > 0:
        day_exit_reason = f"{' & '.join(tp_legs)} TARGET HIT"
    else:
        day_exit_reason = "TIME EXIT"

    # Step 6: Check strategy-level SL/TP
    if config.strategy_sl_points is not None and total_pnl_points <= -abs(config.strategy_sl_points):
        day_exit_reason = "STRATEGY MAX SL HIT"
    elif config.strategy_target_points is not None and total_pnl_points >= config.strategy_target_points:
        day_exit_reason = "STRATEGY TARGET HIT"

    return DailyResult(
        trade_date=trade_date,
        expiry_date=expiry,
        atm_strike=atm_strike,
        underlying_price=underlying_price,
        legs=leg_results,
        total_pnl_points=total_pnl_points,
        total_pnl_value=total_pnl_value,
        exit_reason=day_exit_reason,
    )


def _process_leg(
    leg_config: LegConfig,
    atm_strike: int,
    expiry: date,
    trade_date: date,
    symbol: str,
    lot_size: int,
    parquet_dir: Path | None,
    entry_time: str = "09:56:00",
    exit_time: str = "14:50:00",
) -> LegResult | None:
    """Process a single leg of the strategy for one day using minute-level intraday evaluation when configured."""

    # Resolve the actual strike
    strike = resolve_strike(
        atm_strike, leg_config.strike_selection,
        leg_config.option_type.value, symbol,
    )

    # Get option price for this strike/expiry/date
    price_data = get_option_price(
        symbol, float(strike), leg_config.option_type.value,
        expiry, trade_date, parquet_dir,
    )

    if price_data is None:
        logger.debug(
            "No price data for %s %s %s exp=%s on %s",
            symbol, strike, leg_config.option_type.value, expiry, trade_date,
        )
        return None

    # Use 1-minute intraday simulation when not a full-day positional trade
    if entry_time != "09:15:00" or exit_time != "15:30:00":
        intraday_res = simulate_intraday_leg(
            leg_config, strike, expiry, trade_date,
            symbol, lot_size, price_data,
            entry_time_str=entry_time,
            exit_time_str=exit_time,
        )
        if intraday_res is not None:
            return intraday_res

    entry_price = price_data["open"]  # Using open as entry proxy for daily intraday trades
    if entry_price is None or entry_price <= 0:
        # Fallback to close price
        entry_price = price_data["close"]
        if entry_price is None or entry_price <= 0:
            return None

    # Check SL/target using daily High/Low
    exit_price, exit_reason = _check_leg_sl_target(
        entry_price=entry_price,
        day_high=price_data["high"] or entry_price,
        day_low=price_data["low"] or entry_price,
        action=leg_config.action.value,
        sl_percent=leg_config.sl_percent,
        target_percent=leg_config.target_percent,
        close_price=price_data["close"] or entry_price,
    )

    # Calculate P&L
    pnl_points, pnl_value = _calculate_leg_pnl(
        entry_price, exit_price,
        leg_config.action.value,
        leg_config.lots, lot_size,
    )

    return LegResult(
        option_type=leg_config.option_type.value,
        action=leg_config.action.value,
        strike=float(strike),
        entry_price=entry_price,
        exit_price=exit_price,
        pnl_points=pnl_points,
        lots=leg_config.lots,
        lot_size=lot_size,
        pnl_value=pnl_value,
        exit_reason=exit_reason,
    )
