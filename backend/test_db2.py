from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.papertrade
    strategy = await db.strategies.find_one({"_id": "efabaed1-e3dd-426e-9f80-5aac14f2a248"})
    legs = await db.strategy_legs.find({"strategy_id": "efabaed1-e3dd-426e-9f80-5aac14f2a248"}).to_list(None)
    print("Strategy name:", strategy.get("name") if strategy else "None")
    for leg in legs:
        print("Leg ID:", leg.get("_id"), "Instrument Key:", leg.get("instrument_key"))

asyncio.run(main())
