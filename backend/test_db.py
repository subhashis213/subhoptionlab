import asyncio
from papertrade.db import connect_db, strategy_legs_collection

async def check():
    import papertrade.db as db
    await db.connect_db()
    legs = await db.strategy_legs_collection.find({"strategy_id": "efabaed1-e3dd-426e-9f80-5aac14f2a248"}).to_list(10)
    print([l.get("instrument_key") for l in legs])

asyncio.run(check())
