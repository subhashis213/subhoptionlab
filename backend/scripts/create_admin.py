"""
CLI script to create the first admin user.
Usage: python scripts/create_admin.py

Run this once to seed the admin account.
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()


async def create_admin():
    from papertrade.auth import hash_password

    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("MONGODB_DB_NAME", "option_backtester")

    print(f"\n{'='*50}")
    print("  Paper Trading Platform — Admin Setup")
    print(f"{'='*50}\n")

    name = input("Admin name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = input("Admin password (min 6 chars): ").strip()

    if len(password) < 6:
        print("❌ Password must be at least 6 characters.")
        return

    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    users_col = db["pt_users"]
    wallets_col = db["pt_wallets"]

    # Check if email exists
    existing = await users_col.find_one({"email": email})
    if existing:
        print(f"❌ Email '{email}' already registered.")
        client.close()
        return

    user_id = str(uuid.uuid4())
    user_doc = {
        "_id": user_id,
        "name": name,
        "email": email,
        "phone": "",
        "password_hash": hash_password(password),
        "role": "admin",
        "status": "active",
        "created_at": datetime.utcnow(),
    }
    await users_col.insert_one(user_doc)

    # Create wallet (admin doesn't trade, but has a wallet record)
    await wallets_col.insert_one({
        "user_id": user_id,
        "virtual_chips_balance": 0.0,
        "total_added": 0.0,
        "total_removed": 0.0,
        "last_updated": datetime.utcnow(),
    })

    print(f"\n✅ Admin user created successfully!")
    print(f"   ID:    {user_id}")
    print(f"   Name:  {name}")
    print(f"   Email: {email}")
    print(f"   Role:  admin\n")

    client.close()


if __name__ == "__main__":
    asyncio.run(create_admin())
