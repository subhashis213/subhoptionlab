from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.papertrade
    strats = await db.strategies_collection.find().sort("created_at", -1).to_list(5)
    for s in strats:
        print(f"ID: {s['_id']}, Name: {s.get('name')}, Status: {s.get('status')}")
        legs = await db.strategy_legs_collection.find({"strategy_id": s["_id"]}).to_list(10)
        for l in legs:
            print(f"  Leg: {l['_id']} - Instrument: {l.get('instrument_key')}")

asyncio.run(main())
