import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from papertrade.upstox_guard import fetch_ltp

async def check():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.option_backtester
    strategy_id = "f4ec3825-1f67-4ca9-b936-ab928b0af04a"
    
    legs = await db.pt_strategy_legs.find({"strategy_id": strategy_id}).to_list(10)
    keys = [l["instrument_key"] for l in legs]
    print("Strategy Leg Keys in DB:", keys)
    
    ltps = await fetch_ltp(keys)
    print("Fetched LTPs directly from Upstox API:", ltps)
    
    for l in legs:
        key = l["instrument_key"]
        live_price = ltps.get(key)
        if live_price is not None:
            await db.pt_strategy_legs.update_one(
                {"_id": l["_id"]},
                {"$set": {"current_ltp": live_price}}
            )
            print(f"Updated leg {l['strike']} {l['option_type']} current_ltp to {live_price}")

asyncio.run(check())
