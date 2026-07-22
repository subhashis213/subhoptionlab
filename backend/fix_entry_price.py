import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def fix():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.option_backtester
    
    legs = await db.pt_strategy_legs.find({
        "current_status": "open",
        "entry_price": 0.0
    }).to_list(10)
    
    updates = 0
    for l in legs:
        if l["current_ltp"] > 0:
            await db.pt_strategy_legs.update_one(
                {"_id": l["_id"]},
                {"$set": {"entry_price": l["current_ltp"]}}
            )
            updates += 1
            print(f"Updated leg {l['_id']} entry_price to {l['current_ltp']}")
            
    print(f"Total fixed: {updates}")

asyncio.run(fix())
