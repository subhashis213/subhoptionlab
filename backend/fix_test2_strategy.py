import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from papertrade.upstox_guard import fetch_ltp, build_instrument_key

async def fix():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.option_backtester
    strategy_id = "5da748aa-b848-4dd2-bb57-7f6f057d116f"
    
    legs = await db.pt_strategy_legs.find({"strategy_id": strategy_id}).to_list(10)
    print("Found legs in test2 to update:", len(legs))
    
    # 24000 CE key: NSE_FO|63939, 24000 PE key: NSE_FO|63940
    mapping = {
        "CE": {"strike": 24000.0, "key": "NSE_FO|63939", "entry": 142.00, "ltp": 142.00},
        "PE": {"strike": 24000.0, "key": "NSE_FO|63940", "entry": 173.95, "ltp": 173.95},
    }
    
    for l in legs:
        opt = l.get("option_type", "CE")
        data = mapping[opt]
        await db.pt_strategy_legs.update_one(
            {"_id": l["_id"]},
            {"$set": {
                "strike": data["strike"],
                "instrument_key": data["key"],
                "entry_price": data["entry"],
                "current_ltp": data["ltp"],
                "current_sl_price": data["entry"] + 25.0, # SL for SELL is entry + 25
                "current_status": "open"
            }}
        )
        print(f"Updated test2 leg {opt}: strike=24000, key={data['key']}, entry={data['entry']}, ltp={data['ltp']}")

asyncio.run(fix())
