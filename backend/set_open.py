import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def run():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.option_backtester
    strategy_id = "a7c87de6-38f4-4bed-8387-d681ca46e581"
    
    await db.pt_strategy_legs.update_many(
        {"strategy_id": strategy_id},
        {"$set": {
            "current_status": "open",
            "exit_price": None,
            "exit_reason": None,
            "entry_price": 145.25,
            "current_ltp": 142.50
        }}
    )
    print("Reset status to open for strategy", strategy_id)

asyncio.run(run())
