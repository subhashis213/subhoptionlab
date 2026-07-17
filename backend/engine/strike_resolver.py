"""
Strike Resolver — maps strike selection strings to actual strike prices.

Handles ATM, ITM-n, OTM-n relative strike selection for both CE and PE options.

For CE options:
  - ITM = strikes BELOW ATM (in-the-money for calls)
  - OTM = strikes ABOVE ATM (out-of-the-money for calls)

For PE options:
  - ITM = strikes ABOVE ATM (in-the-money for puts)
  - OTM = strikes BELOW ATM (out-of-the-money for puts)
"""

import re
from config import STRIKE_INTERVALS


def resolve_strike(
    atm_strike: int,
    selection: str,
    option_type: str,
    symbol: str,
) -> int:
    """
    Resolve a strike selection string to an actual strike price.

    Args:
        atm_strike: The ATM strike price (already rounded to valid interval).
        selection: Strike selection string, e.g. "ATM", "ITM-1", "OTM-3".
        option_type: "CE" or "PE".
        symbol: Index symbol (determines strike interval).

    Returns:
        The resolved strike price.

    Examples:
        >>> resolve_strike(48000, "ATM", "CE", "BANKNIFTY")
        48000
        >>> resolve_strike(48000, "OTM-2", "CE", "BANKNIFTY")
        48200
        >>> resolve_strike(48000, "ITM-1", "CE", "BANKNIFTY")
        47900
        >>> resolve_strike(48000, "OTM-2", "PE", "BANKNIFTY")
        47800
    """
    interval = STRIKE_INTERVALS.get(symbol.upper())
    if interval is None:
        raise ValueError(f"Unknown symbol: {symbol}")

    selection = selection.strip().upper()

    # Parse the selection string
    if selection == "ATM":
        return atm_strike

    match = re.match(r"^(ITM|OTM)[- ]?(\d+)$", selection)
    if not match:
        raise ValueError(
            f"Invalid strike selection: '{selection}'. "
            "Expected 'ATM', 'ITM-n', or 'OTM-n'."
        )

    direction = match.group(1)  # ITM or OTM
    steps = int(match.group(2))

    # Calculate offset in strike price units
    offset = steps * interval

    if option_type.upper() == "CE":
        if direction == "OTM":
            # OTM for CE = higher strikes
            return atm_strike + offset
        else:  # ITM
            # ITM for CE = lower strikes
            return atm_strike - offset

    elif option_type.upper() == "PE":
        if direction == "OTM":
            # OTM for PE = lower strikes
            return atm_strike - offset
        else:  # ITM
            # ITM for PE = higher strikes
            return atm_strike + offset

    else:
        raise ValueError(f"Invalid option type: {option_type}. Expected 'CE' or 'PE'.")
