import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def simulate():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.option_backtester
    
    legs = await db.pt_strategy_legs.find({
        "current_status": "open",
        "strategy_id": "5bad1dd0-34c7-4192-8517-fe6016b7ab63"
    }).to_list(10)
    
    if len(legs) >= 2:
        # Offset the first leg by -10 points (creating a fake profit for a BUY, or fake loss for a SELL)
        await db.pt_strategy_legs.update_one(
            {"_id": legs[0]["_id"]},
            {"$set": {"entry_price": 587.00}}
        )
        
        # Offset the second leg by +15 points
        await db.pt_strategy_legs.update_one(
            {"_id": legs[1]["_id"]},
            {"$set": {"entry_price": 562.00}}
        )
        print("Updated entry prices to simulate P&L!")

asyncio.run(simulate())
