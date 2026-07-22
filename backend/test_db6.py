from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from datetime import datetime

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.options_backtester
    strategy_id = "efabaed1-e3dd-426e-9f80-5aac14f2a248"
    s = await db.pt_strategies.find_one({"_id": strategy_id})
    if s:
        print(f"ID: {s['_id']}, Name: {s.get('name')}, Status: {s.get('status')}")
        legs = await db.pt_strategy_legs.find({"strategy_id": s["_id"]}).to_list(10)
        for l in legs:
            print(f"  Leg: {l['_id']} - Instrument: {l.get('instrument_key')} - Expiry: {l.get('expiry')} - Strike: {l.get('strike')} {l.get('option_type')}")
    else:
        print("Strategy not found!")

asyncio.run(main())
