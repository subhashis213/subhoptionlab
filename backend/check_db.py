import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def main():
    uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(uri)
    db = client["option_backtester"]
    
    user = await db.pt_users.find_one({"email": "subhashissahu213@gmail.com"})
    print("User:", user)
    
    if user:
        wallet = await db.pt_wallets.find_one({"user_id": user["_id"]})
        print("Wallet by string ID:", wallet)
        
        wallet2 = await db.pt_wallets.find_one({"user_id": str(user["_id"])})
        print("Wallet by str(ID):", wallet2)

        wallets = await db.pt_wallets.find().to_list(length=10)
        print("All wallets:")
        for w in wallets:
            print(w)

asyncio.run(main())
