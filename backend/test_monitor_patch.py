import re

STRIKE_STEPS = {
    "NIFTY": 50,
    "BANKNIFTY": 100,
    "FINNIFTY": 50,
    "MIDCAPNIFTY": 25
}

def resolve_dynamic_strike(strike_str: str, spot_price: float, underlying: str, option_type: str) -> float:
    step = STRIKE_STEPS.get(underlying, 50)
    atm = round(spot_price / step) * step
    
    if strike_str == "ATM":
        return atm
    
    # parse ITM1, OTM2, etc.
    match = re.match(r"(ITM|OTM)(\d+)", strike_str)
    if match:
        type_ = match.group(1)
        offset = int(match.group(2))
        
        # CE: ITM is lower strike, OTM is higher strike
        # PE: ITM is higher strike, OTM is lower strike
        if option_type == "CE":
            if type_ == "ITM":
                return atm - (offset * step)
            else:
                return atm + (offset * step)
        else:
            if type_ == "ITM":
                return atm + (offset * step)
            else:
                return atm - (offset * step)
    
    # Fallback if unparseable
    return atm

print(resolve_dynamic_strike("ATM", 24021.5, "NIFTY", "CE")) # 24000
print(resolve_dynamic_strike("ITM1", 24021.5, "NIFTY", "CE")) # 23950
print(resolve_dynamic_strike("OTM2", 24021.5, "NIFTY", "PE")) # 23900 (Wait, OTM PE means lower strike, 24000 - 100 = 23900. Correct!)
