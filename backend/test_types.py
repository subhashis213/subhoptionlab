import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def main():
    uri = os.getenv("MONGODB_URI") + "&tlsAllowInvalidCertificates=true"
    client = AsyncIOMotorClient(uri)
    db = client.option_backtester # Check DB name in config.py! Wait, config.py says MONGODB_DB_NAME is option_backtester
    
    # get a user
    user = await db.users.find_one({"email": "subhashis213@gmail.com"})
    if not user:
        print("User not found!")
    else:
        print(f"User ID: {user['_id']}, Type: {type(user['_id'])}")
        
    # get wallet
    wallets = await db.pt_wallets.find().to_list(10)
    print("Wallets:")
    for w in wallets:
        print(f" - ID: {w['_id']}, user_id: {w['user_id']}, Type: {type(w['user_id'])}, balance: {w.get('virtual_chips_balance')}")

if __name__ == "__main__":
    asyncio.run(main())
