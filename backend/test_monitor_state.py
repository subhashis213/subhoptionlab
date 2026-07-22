import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def check():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.option_backtester
    
    legs = await db.pt_strategy_legs.find({
        "current_status": "open"
    }).to_list(10)
    
    print(f"Found {len(legs)} open legs.")
    for l in legs:
        print(f"Strategy: {l['strategy_id']}, Leg: {l['instrument_key']}, LTP: {l['current_ltp']}, PNL?: {l.get('unrealized_pnl', 0)}")

asyncio.run(check())
