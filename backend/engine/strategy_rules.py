"""
Shared Strategy Rules Engine.

Contains pure, stateless logic for evaluating stop loss, targets, and trailing rules.
By extracting this into a shared module, we guarantee that the backtest simulator
and the live/paper trading engine evaluate exact identical rules, ensuring that
paper trading results are trustworthy previews of live trading behavior.
"""

def calculate_sl_price(
    entry_price: float,
    sl_percent: float,
    action: str,
) -> float:
    """
    Calculate the stop loss trigger price based on entry price and percentage.

    For SELL: SL is when price RISES by sl_percent from entry → loss for seller.
    For BUY: SL is when price FALLS by sl_percent from entry → loss for buyer.
    """
    if sl_percent <= 0:
        return 0.0

    if action == "SELL":
        return entry_price * (1 + sl_percent / 100)
    else:  # BUY
        return entry_price * max(0.01, 1 - sl_percent / 100)


def calculate_target_price(
    entry_price: float,
    target_percent: float,
    action: str,
) -> float:
    """
    Calculate the target profit trigger price.

    For SELL: Target is when price FALLS by target_percent → profit for seller.
    For BUY: Target is when price RISES by target_percent → profit for buyer.
    """
    if target_percent <= 0:
        return 0.0

    if action == "SELL":
        return entry_price * max(0.01, 1 - target_percent / 100)
    else:  # BUY
        return entry_price * (1 + target_percent / 100)


def check_leg_sl_target_daily(
    entry_price: float,
    day_high: float,
    day_low: float,
    action: str,
    sl_percent: float | None,
    target_percent: float | None,
    close_price: float,
) -> tuple[float, str]:
    """
    Check if a leg's SL or target was hit using daily OHLC proxy (used by historical backtest).

    Returns:
        (exit_price, exit_reason) where exit_reason is one of:
        "leg_sl_hit", "leg_target_hit", "time_exit"
    """
    sl_hit = False
    target_hit = False
    sl_exit_price = close_price
    target_exit_price = close_price

    if sl_percent is not None and sl_percent > 0:
        sl_price = calculate_sl_price(entry_price, sl_percent, action)
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
        target_price = calculate_target_price(entry_price, target_percent, action)
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

    # If both could trigger, assume SL hit first (conservative for backtesting)
    if sl_hit and target_hit:
        return sl_exit_price, "leg_sl_hit"
    elif sl_hit:
        return sl_exit_price, "leg_sl_hit"
    elif target_hit:
        return target_exit_price, "leg_target_hit"
    else:
        return close_price, "time_exit"


def evaluate_leg_rules_tick(
    current_price: float,
    action: str,
    sl_price: float | None,
    target_price: float | None,
) -> str | None:
    """
    Evaluate if SL or target is hit at the current exact tick/minute price.
    Used by intraday minute simulator AND the live/paper trading runner.

    Returns:
        Exit reason string ("leg_sl_hit" or "leg_target_hit") if a rule triggers,
        otherwise None.
    """
    if sl_price is not None and sl_price > 0:
        if action == "SELL" and current_price >= sl_price:
            return "leg_sl_hit"
        elif action == "BUY" and current_price <= sl_price:
            return "leg_sl_hit"

    if target_price is not None and target_price > 0:
        if action == "SELL" and current_price <= target_price:
            return "leg_target_hit"
        elif action == "BUY" and current_price >= target_price:
            return "leg_target_hit"

    return None
