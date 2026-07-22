import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from papertrade.upstox_guard import resolve_instrument_keys
from dotenv import load_dotenv

load_dotenv()

async def fix():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.option_backtester
    legs = await db.pt_strategy_legs.find({"strategy_id": "efabaed1-e3dd-426e-9f80-5aac14f2a248"}).to_list(10)
    print("Found legs:", len(legs))
    
    # Temporarily set expiry to current_month so it fetches the real one
    for l in legs:
        l["expiry"] = "current_month"
        
    await resolve_instrument_keys(legs)
    
    for l in legs:
        print(f"New key: {l.get('instrument_key')}")
        await db.pt_strategy_legs.update_one({"_id": l["_id"]}, {"$set": {"instrument_key": l["instrument_key"], "expiry": "current_month"}})
        
asyncio.run(fix())
