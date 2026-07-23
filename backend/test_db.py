import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def main():
    client = AsyncIOMotorClient(os.getenv("MONGODB_URI", "mongodb+srv://subhashis213:o2a3O4D162YdJ1S7@cluster0.kavok.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0") + "&tlsAllowInvalidCertificates=true")
    db = client.backtester
    
    # get a user
    user = await db.users_collection.find_one({"email": "subhashis213@gmail.com"})
    if not user:
        print("User not found!")
        return

    # find latest strategy
    strat = await db.strategies_collection.find_one({"user_id": user["_id"]}, sort=[("created_at", -1)])
    if not strat:
        print("No strategies found!")
        return
        
    print(f"Latest Strategy: {strat['name']}, Status: {strat['status']}")
    legs = await db.strategy_legs_collection.find({"strategy_id": strat["_id"]}).to_list(10)
    print("Legs:", len(legs))
    for leg in legs:
        print(f" - {leg.get('symbol')} {leg.get('strike')} {leg.get('option_type')}, status: {leg.get('current_status')}, entry: {leg.get('entry_price')}")

if __name__ == "__main__":
    asyncio.run(main())
