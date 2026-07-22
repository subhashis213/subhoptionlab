"""
MongoDB connection and collection initialization for Paper Trading platform.
Uses Motor async driver. Collections are prefixed with 'pt_' to avoid collisions
with the existing backtester collections.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Collection references — set during init
users_collection = None
wallets_collection = None
chip_transactions_collection = None
strategies_collection = None
strategy_legs_collection = None
trade_history_collection = None


async def init_papertrade_collections(db: AsyncIOMotorDatabase):
    """
    Initialize all paper trading collections and create indexes.
    Called from the main app startup after MongoDB connection is established.
    """
    global users_collection, wallets_collection, chip_transactions_collection
    global strategies_collection, strategy_legs_collection, trade_history_collection

    users_collection = db["pt_users"]
    wallets_collection = db["pt_wallets"]
    chip_transactions_collection = db["pt_chip_transactions"]
    strategies_collection = db["pt_strategies"]
    strategy_legs_collection = db["pt_strategy_legs"]
    trade_history_collection = db["pt_trade_history"]

    # Create indexes
    await users_collection.create_index("email", unique=True)
    await wallets_collection.create_index("user_id", unique=True)
    await chip_transactions_collection.create_index("user_id")
    await chip_transactions_collection.create_index("timestamp")
    await strategies_collection.create_index("user_id")
    await strategies_collection.create_index("status")
    await strategy_legs_collection.create_index("strategy_id")
    await strategy_legs_collection.create_index("current_status")
    await trade_history_collection.create_index("strategy_id")
    await trade_history_collection.create_index("user_id")
    await trade_history_collection.create_index("timestamp")

    logger.info("Paper trading collections initialized with indexes.")
