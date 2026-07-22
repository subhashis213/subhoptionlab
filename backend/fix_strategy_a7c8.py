import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from papertrade.upstox_guard import resolve_instrument_keys, fetch_ltp, build_instrument_key
import re

async def fix():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.option_backtester
    
    strategy_id = "a7c87de6-38f4-4bed-8387-d681ca46e581"
    legs = await db.pt_strategy_legs.find({"strategy_id": strategy_id}).to_list(20)
    print("Found legs to repair:", len(legs))
    
    defaults = {"NIFTY": 24180.6, "BANKNIFTY": 57968.6, "FINNIFTY": 23500.0, "MIDCAPNIFTY": 12500.0}
    steps = {"NIFTY": 50, "BANKNIFTY": 100, "FINNIFTY": 50, "MIDCAPNIFTY": 25}
    
    for l in legs:
        symbol = l.get("symbol", "NIFTY")
        spot = defaults.get(symbol, 24180.6)
        step = steps.get(symbol, 50)
        atm = round(spot / step) * step
        strike_val = l.get("strike")
        resolved_strike = float(atm)
        
        if isinstance(strike_val, str):
            match = re.match(r"^(ITM|OTM)(\d+)$", strike_val.upper().strip())
            if match:
                type_ = match.group(1)
                offset = int(match.group(2))
                if l.get("option_type") == "CE":
                    resolved_strike = float(atm - (offset * step) if type_ == "ITM" else atm + (offset * step))
                else:
                    resolved_strike = float(atm + (offset * step) if type_ == "ITM" else atm - (offset * step))
        
        key = build_instrument_key(symbol, l["expiry"], resolved_strike, l.get("option_type", "CE"))
        ltp_map = await fetch_ltp([key])
        ltp = ltp_map.get(key, 145.25)
        
        await db.pt_strategy_legs.update_one(
            {"_id": l["_id"]},
            {"$set": {
                "strike": resolved_strike,
                "instrument_key": key,
                "entry_price": ltp,
                "current_ltp": ltp
            }}
        )
        print(f"Repaired leg {l['_id']}: strike={resolved_strike}, key={key}, entry={ltp}, ltp={ltp}")

asyncio.run(fix())
