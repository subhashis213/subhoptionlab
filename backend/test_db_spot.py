from datetime import date
from data.queries import get_underlying_price, resolve_atm_strike

p_nifty = get_underlying_price("NIFTY", date(2026, 7, 21), "15:15:00")
p_bank = get_underlying_price("BANKNIFTY", date(2026, 7, 21), "15:15:00")

print("NIFTY spot:", p_nifty, "ATM:", resolve_atm_strike("NIFTY", p_nifty) if p_nifty else None)
print("BANKNIFTY spot:", p_bank, "ATM:", resolve_atm_strike("BANKNIFTY", p_bank) if p_bank else None)
