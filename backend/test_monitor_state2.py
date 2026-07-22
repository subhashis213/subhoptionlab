import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.option_backtester
    
    legs = await db.pt_strategy_legs.find({
        "current_status": "open"
    }).to_list(10)
    
    for l in legs:
        print(f"Leg: {l['instrument_key']}, Entry: {l['entry_price']}, LTP: {l['current_ltp']}")

asyncio.run(check())
