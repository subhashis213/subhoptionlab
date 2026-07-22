"""
Live/Paper Trading Runner Service.
Continuously evaluates active deployed strategies against live ticks.
"""

import asyncio
import logging
from datetime import datetime
import uuid

from live import db
from live.feed import feed_manager
from engine.strategy_rules import evaluate_leg_rules_tick
import json
from config import DATA_DIR

def _get_strategy_config(strategy_id):
    strat_file = DATA_DIR / "saved_strategies.json"
    if strat_file.exists():
        with open(strat_file, "r") as f:
            strats = json.load(f)
            return strats.get(strategy_id)
    return None

logger = logging.getLogger(__name__)


class TradingRunner:
    def __init__(self):
        self._running = False
        self._task = None

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_loop())
            logger.info("Trading runner started.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            logger.info("Trading runner stopped.")

    async def _run_loop(self):
        """Main polling loop for evaluating active strategies."""
        while self._running:
            try:
                await self._evaluate_strategies()
            except Exception as e:
                logger.error(f"Error in runner loop: {e}")
            
            await asyncio.sleep(1)  # Evaluate every second

    async def _evaluate_strategies(self):
        """Fetch active strategies and check their rules."""
        if db.live_strategies_collection is None:
            return

        cursor = db.live_strategies_collection.find({"status": {"$in": ["active", "waiting"]}})
        active_strategies = await cursor.to_list(length=100)
        
        current_time_str = datetime.now().strftime("%H:%M:%S")
        
        for strategy in active_strategies:
            strat_id = strategy["_id"]
            
            if strategy["status"] == "waiting":
                config = _get_strategy_config(strategy["strategy_id"])
                if not config:
                    continue
                entry_time = config["config"].get("entry_time", "09:15:00")
                if current_time_str >= entry_time:
                    # Time to enter!
                    await self._enter_strategy(strategy, config)
                continue
            
            # Fetch open positions for this strategy
            pos_cursor = db.live_positions_collection.find({
                "live_strategy_id": strat_id,
                "status": "open"
            })
            open_positions = await pos_cursor.to_list(length=100)
            
            # Fetch original backtest strategy to get SL/TP percentages
            # For simplicity in this demo, we assume the legs' target/SL logic
            # is stored directly in the position or we fetch from saved JSON.
            # In production, we'd hydrate the full strategy schema.
            # For this basic implementation, we'll evaluate if the user hit max_daily_loss.
            
            total_unrealized_pnl = 0.0
            total_realized_pnl = 0.0
            
            for pos in open_positions:
                leg_idx = pos["leg_index"]
                entry_price = pos["entry_price"]
                action = pos.get("action", "SELL")
                sl_price = pos.get("sl_price")
                target_price = pos.get("target_price")
                instrument = pos.get("instrument_token", "MOCK_INST")
                
                # Get current price from feed
                current_price = feed_manager.latest_quotes.get(instrument, pos["current_price"])
                
                # Calculate leg PNL (simplified 1 lot size for demo)
                leg_pnl = (entry_price - current_price) if action == "SELL" else (current_price - entry_price)
                total_unrealized_pnl += leg_pnl
                
                # Evaluate tick rules (Engine-side monitoring)
                exit_reason = evaluate_leg_rules_tick(
                    current_price=current_price,
                    action=action,
                    sl_price=sl_price,
                    target_price=target_price
                )
                
                if exit_reason:
                    logger.info(f"Leg {leg_idx} in strategy {strat_id} hit {exit_reason} at {current_price}")
                    await self._execute_exit(strat_id, pos, current_price, exit_reason)
                else:
                    # Update current price in DB
                    await db.live_positions_collection.update_one(
                        {"_id": pos["_id"]},
                        {"$set": {"current_price": current_price, "unrealized_pnl": leg_pnl, "updated_at": datetime.utcnow()}}
                    )

            # Check strategy-level max daily loss
            if strategy.get("max_daily_loss") and total_unrealized_pnl <= -abs(strategy["max_daily_loss"]):
                logger.warning(f"Strategy {strat_id} hit MAX DAILY LOSS. Square off triggered.")
                await self._kill_strategy(strat_id, "MAX_DAILY_LOSS")

    async def _execute_exit(self, strat_id: str, position: dict, exit_price: float, reason: str):
        """Simulate an exit execution."""
        
        # 1. Calculate precise realized PnL
        entry_price = position.get("entry_price", 0.0)
        qty = position.get("qty", 15)
        is_buy = position.get("action", "SELL") == "BUY"
        
        if is_buy:
            realized_pnl = (exit_price - entry_price) * qty
        else:
            realized_pnl = (entry_price - exit_price) * qty

        # 2. Close position
        await db.live_positions_collection.update_one(
            {"_id": position["_id"]},
            {"$set": {
                "status": "closed",
                "current_price": exit_price,
                "realized_pnl": realized_pnl,
                "updated_at": datetime.utcnow()
            }}
        )
        
        # 3. Update Paper Trading Wallet
        # Only if strategy mode is paper
        strat = await db.live_strategies_collection.find_one({"_id": strat_id})
        if strat and strat.get("mode") == "paper":
            await db.wallet_collection.update_one(
                {"user_id": strat.get("user_id", "default_user")},
                {"$inc": {"balance": realized_pnl}},
                upsert=True
            )
        
        # 2. Record Exit Order
        order = {
            "_id": str(uuid.uuid4()),
            "live_strategy_id": strat_id,
            "leg_index": position["leg_index"],
            "action": "BUY" if position.get("action", "SELL") == "SELL" else "SELL",
            "symbol": position.get("symbol", "UNKNOWN"),
            "strike": position.get("strike", 0.0),
            "option_type": position.get("option_type", "CE"),
            "order_type": "exit",
            "price": exit_price,
            "qty": position.get("qty", 15),
            "timestamp": datetime.utcnow(),
            "exit_reason": reason,
            "broker_order_id": None # None for paper trading
        }
        await db.live_orders_collection.insert_one(order)

    async def _enter_strategy(self, strategy, config):
        """Simulate entry orders when entry time is reached."""
        strat_id = strategy["_id"]
        symbol = config["config"].get("symbol", "BANKNIFTY")
        mock_token = f"{symbol}_MOCK_TOKEN"
        feed_manager.subscribe(mock_token)
        
        for i, leg in enumerate(config["config"].get("legs", [])):
            pos = {
                "_id": str(uuid.uuid4()),
                "live_strategy_id": strat_id,
                "leg_index": i,
                "status": "open",
                "action": leg.get("action", "SELL"),
                "option_type": leg.get("option_type", "CE"),
                "symbol": symbol,
                "instrument_token": mock_token,
                "entry_price": 100.0,
                "current_price": 100.0,
                "qty": 15 * strategy.get("max_lots", 1) * leg.get("lots", 1),  # Assuming 15 as base lot size for BANKNIFTY
                "sl_percent": leg.get("sl_percent"),
                "target_percent": leg.get("target_percent"),
                "sl_price": 100.0 * (1 + (leg.get("sl_percent") or 0)/100) if leg.get("action") == "SELL" else 100.0 * (1 - (leg.get("sl_percent") or 0)/100),
                "target_price": 100.0 * (1 - (leg.get("target_percent") or 0)/100) if leg.get("action") == "SELL" else 100.0 * (1 + (leg.get("target_percent") or 0)/100),
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
                "updated_at": datetime.utcnow()
            }
            await db.live_positions_collection.insert_one(pos)
        
        await db.live_strategies_collection.update_one(
            {"_id": strat_id},
            {"$set": {"status": "active"}}
        )
        logger.info(f"Strategy {strat_id} entered positions (Entry Time Reached).")

    async def _kill_strategy(self, strat_id: str, reason: str):
        """Close all open positions for a strategy immediately."""
        # Get all open positions
        cursor = db.live_positions_collection.find({
            "live_strategy_id": strat_id,
            "status": "open"
        })
        open_positions = await cursor.to_list(length=100)
        
        for pos in open_positions:
            inst = pos.get("instrument_token", "MOCK_INST")
            current_price = feed_manager.latest_quotes.get(inst, pos["current_price"])
            await self._execute_exit(strat_id, pos, current_price, reason)
            
        # Update strategy status
        await db.live_strategies_collection.update_one(
            {"_id": strat_id},
            {"$set": {"status": "killed", "stopped_at": datetime.utcnow()}}
        )

# Global singleton runner
runner_service = TradingRunner()
