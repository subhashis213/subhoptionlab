"""
Background SL/Target Monitoring Service.

Runs every 3 seconds during market hours (9:15 AM – 3:30 PM IST).
Monitors all open legs across all users, checks SL/target hits,
implements move-SL-to-cost logic, and pushes updates via WebSocket.

PAPER TRADE ONLY — uses upstox_guard for price data (no order execution).
"""

import asyncio
import uuid
import logging
from datetime import datetime, timezone, timedelta

from papertrade import db
from papertrade.upstox_guard import fetch_ltp, build_instrument_key
from papertrade.router_markets import INDICES
from config import LOT_SIZES
import re

logger = logging.getLogger(__name__)

# IST timezone offset
IST = timezone(timedelta(hours=5, minutes=30))

# Market hours
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MIN = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MIN = 30


class MonitorService:
    """
    Background service that monitors all open paper trading legs.
    Checks SL/target prices against live LTP and executes paper exits.
    """

    def __init__(self):
        self._running = False
        self._task = None
        self._ws_manager = None  # Set externally after import

    def set_ws_manager(self, ws_manager):
        """Inject WebSocket manager for live updates."""
        self._ws_manager = ws_manager

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_loop())
            logger.info("Paper trade monitor service started.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            logger.info("Paper trade monitor service stopped.")

    def _is_market_hours(self) -> bool:
        """Check if current IST time is within market hours."""
        now_ist = datetime.now(IST)
        market_open = now_ist.replace(
            hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MIN, second=0, microsecond=0
        )
        market_close = now_ist.replace(
            hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MIN, second=0, microsecond=0
        )
        return market_open <= now_ist <= market_close

    async def _run_loop(self):
        """Main polling loop — every 2 seconds during market hours, auto-closes after 15:30 IST."""
        while self._running:
            try:
                if self._is_market_hours():
                    await self._monitor_pending_strategies()
                    await self._monitor_all_legs()
                    await self._monitor_exits()
                else:
                    # Outside market hours: immediately check and auto-close any active strategies
                    await self._close_active_strategies_market_close()
                    logger.debug("Outside market hours, monitor sleeping...")
            except Exception as e:
                import traceback
                logger.error(f"Error in runner loop: {e}\n{traceback.format_exc()}")
            
            await asyncio.sleep(2)

    async def _monitor_exits(self):
        """Check 'active' strategies and exit all open legs if exit_time is met or market closed (15:30 IST)."""
        if db.strategies_collection is None:
            return

        now_ist = datetime.now(IST)
        current_hhmm = now_ist.strftime("%H:%M")

        # Find active strategies where exit_time <= current time OR current time >= 15:30
        if current_hhmm >= "15:30":
            query = {"status": "active"}
        else:
            query = {
                "status": "active",
                "exit_time": {"$lte": current_hhmm, "$nin": [None, ""]}
            }

        exit_cursor = db.strategies_collection.find(query)
        exit_strats = await exit_cursor.to_list(length=100)

        for strat in exit_strats:
            strat_id = strat["_id"]
            user_id = strat["user_id"]
            
            # Fetch open legs
            legs_cursor = db.strategy_legs_collection.find({
                "strategy_id": strat_id, 
                "current_status": "open"
            })
            open_legs = await legs_cursor.to_list(length=100)
            
            if not open_legs:
                await db.strategies_collection.update_one({"_id": strat_id}, {"$set": {"status": "closed", "closed_at": datetime.now(timezone.utc)}})
                continue

            # Fetch LTP for closing
            instrument_keys = [leg["instrument_key"] for leg in open_legs if leg.get("instrument_key")]
            ltp_data = await fetch_ltp(instrument_keys) if instrument_keys else {}

            for leg in open_legs:
                inst_key = leg.get("instrument_key", "")
                exit_price = ltp_data.get(inst_key) or leg.get("current_ltp") or leg.get("entry_price") or 0.0
                
                entry_price = leg["entry_price"]
                qty = leg["qty"]
                lot_size = LOT_SIZES.get(leg.get("symbol", "NIFTY"), 50)
                total_qty = qty * lot_size
                
                pnl = (exit_price - entry_price) * total_qty if leg["side"] == "BUY" else (entry_price - exit_price) * total_qty
                
                # Update leg
                await db.strategy_legs_collection.update_one(
                    {"_id": leg["_id"]},
                    {"$set": {
                        "current_status": "manually_closed",
                        "exit_price": exit_price,
                        "exit_reason": "market_close" if current_hhmm >= "15:30" else "time_exit",
                        "current_ltp": exit_price
                    }}
                )
                
                # Update wallet
                await db.wallets_collection.update_one(
                    {"user_id": user_id},
                    {"$inc": {"virtual_chips_balance": pnl}}
                )
                
                # Trade history
                trade_doc = {
                    "_id": str(uuid.uuid4()),
                    "strategy_id": strat_id,
                    "leg_id": leg["_id"],
                    "user_id": user_id,
                    "action": "SELL" if leg["side"] == "BUY" else "BUY",
                    "symbol": leg.get("symbol", ""),
                    "strike": leg.get("strike", 0),
                    "option_type": leg.get("option_type", "CE"),
                    "price": exit_price,
                    "qty": qty,
                    "pnl": pnl,
                    "exit_reason": "market_close" if current_hhmm >= "15:30" else "time_exit",
                    "timestamp": datetime.now(timezone.utc),
                }
                await db.trade_history_collection.insert_one(trade_doc)

            # Close strategy
            await db.strategies_collection.update_one({"_id": strat_id}, {"$set": {"status": "closed", "closed_at": datetime.now(timezone.utc)}})
            logger.info(f"Auto-closed strategy {strat_id} at {current_hhmm}")

    async def _close_active_strategies_market_close(self):
        """Auto-close any remaining active strategies after market hours (3:30 PM IST)."""
        if db.strategies_collection is None:
            return

        now_ist = datetime.now(IST)
        current_hhmm = now_ist.strftime("%H:%M")

        # Find any active strategies still remaining
        exit_cursor = db.strategies_collection.find({"status": "active"})
        exit_strats = await exit_cursor.to_list(length=100)

        if not exit_strats:
            return

        logger.info(f"Market closed ({current_hhmm} IST). Auto-closing {len(exit_strats)} remaining active strategies...")

        for strat in exit_strats:
            strat_id = strat["_id"]
            user_id = strat["user_id"]
            
            # Fetch open legs
            legs_cursor = db.strategy_legs_collection.find({
                "strategy_id": strat_id, 
                "current_status": "open"
            })
            open_legs = await legs_cursor.to_list(length=100)
            
            if not open_legs:
                await db.strategies_collection.update_one({"_id": strat_id}, {"$set": {"status": "closed", "closed_at": datetime.now(timezone.utc)}})
                continue

            # Fetch LTP for closing
            instrument_keys = [leg["instrument_key"] for leg in open_legs if leg.get("instrument_key")]
            ltp_data = await fetch_ltp(instrument_keys) if instrument_keys else {}

            for leg in open_legs:
                inst_key = leg.get("instrument_key", "")
                exit_price = ltp_data.get(inst_key) or leg.get("current_ltp") or leg.get("entry_price") or 0.0
                
                entry_price = leg.get("entry_price", 0.0)
                qty = leg.get("qty", 1)
                lot_size = LOT_SIZES.get(leg.get("symbol", "NIFTY"), 50)
                total_qty = qty * lot_size
                
                pnl = (exit_price - entry_price) * total_qty if leg["side"] == "BUY" else (entry_price - exit_price) * total_qty
                
                # Update leg
                await db.strategy_legs_collection.update_one(
                    {"_id": leg["_id"]},
                    {"$set": {
                        "current_status": "manually_closed",
                        "exit_price": exit_price,
                        "exit_reason": "market_close",
                        "current_ltp": exit_price
                    }}
                )
                
                # Update wallet
                await db.wallets_collection.update_one(
                    {"user_id": user_id},
                    {"$inc": {"virtual_chips_balance": pnl}}
                )
                
                # Trade history
                trade_doc = {
                    "_id": str(uuid.uuid4()),
                    "strategy_id": strat_id,
                    "leg_id": leg["_id"],
                    "user_id": user_id,
                    "action": "SELL" if leg["side"] == "BUY" else "BUY",
                    "symbol": leg.get("symbol", ""),
                    "strike": leg.get("strike", 0),
                    "option_type": leg.get("option_type", "CE"),
                    "price": exit_price,
                    "qty": qty,
                    "pnl": pnl,
                    "exit_reason": "market_close",
                    "timestamp": datetime.now(timezone.utc),
                }
                await db.trade_history_collection.insert_one(trade_doc)

            # Close strategy
            await db.strategies_collection.update_one({"_id": strat_id}, {"$set": {"status": "closed", "closed_at": datetime.now(timezone.utc)}})
            logger.info(f"Auto-closed strategy {strat_id} at market close ({current_hhmm} IST).")
            
            # Broadcast WebSocket notification
            if self._ws_manager:
                await self._ws_manager.broadcast({
                    "type": "strategy_closed",
                    "strategy_id": strat_id,
                    "reason": "market_close"
                })

    async def _monitor_pending_strategies(self):
        """Check 'pending' strategies and activate if entry_time is met."""
        if db.strategies_collection is None:
            return

        now_ist = datetime.now(IST)
        current_hhmm = now_ist.strftime("%H:%M")

        # Find pending strategies where entry_time <= current time
        pending_cursor = db.strategies_collection.find({
            "status": "pending",
            "entry_time": {"$lte": current_hhmm, "$nin": [None, ""]}
        })
        pending_strats = await pending_cursor.to_list(length=100)
        
        if not pending_strats:
            return
            
        # Optimization: fetch index spot prices if there are dynamic strikes to resolve
        keys = list(INDICES.values())
        index_quotes = await fetch_ltp(keys)

        for strat in pending_strats:
            strat_id = strat["_id"]
            # Get legs
            legs_cursor = db.strategy_legs_collection.find({"strategy_id": strat_id})
            legs = await legs_cursor.to_list(length=20)
            
            if not legs:
                await db.strategies_collection.update_one({"_id": strat_id}, {"$set": {"status": "active"}})
                continue

            # 1. Resolve dynamic strikes (ATM/ITM/OTM) and build instrument keys
            for leg in legs:
                strike_val = leg.get("strike")
                if leg.get("instrument_key") is None or isinstance(strike_val, str):
                    underlying = leg.get("symbol", strat.get("underlying"))
                    option_type = leg.get("option_type", "CE")
                    index_key = INDICES.get(underlying)
                    spot_price = index_quotes.get(index_key, 0.0) if index_key else 0.0
                    
                    if spot_price > 0:
                        # Step sizing
                        steps = {"NIFTY": 50, "BANKNIFTY": 100, "FINNIFTY": 50, "MIDCAPNIFTY": 25}
                        step = steps.get(underlying, 50)
                        atm = round(spot_price / step) * step
                        resolved_strike = atm
                        
                        if isinstance(strike_val, str):
                            match = re.match(r"(ITM|OTM)(\d+)", strike_val)
                            if match:
                                type_ = match.group(1)
                                offset = int(match.group(2))
                                if option_type == "CE":
                                    resolved_strike = atm - (offset * step) if type_ == "ITM" else atm + (offset * step)
                                else:
                                    resolved_strike = atm + (offset * step) if type_ == "ITM" else atm - (offset * step)

                        leg["strike"] = resolved_strike
                        leg["instrument_key"] = build_instrument_key(underlying, leg["expiry"], resolved_strike, option_type)
                        
                        # Update leg in DB
                        await db.strategy_legs_collection.update_one(
                            {"_id": leg["_id"]},
                            {"$set": {"strike": resolved_strike, "instrument_key": leg["instrument_key"]}}
                        )

            # Batch fetch LTP for Market entries
            instrument_keys = [leg["instrument_key"] for leg in legs if leg.get("instrument_key") and leg.get("order_type") != "LIMIT"]
            ltp_data = await fetch_ltp(instrument_keys) if instrument_keys else {}

            for leg in legs:
                if leg.get("order_type") == "LIMIT":
                    # Leave as pending_entry, engine will handle it
                    continue

                inst_key = leg.get("instrument_key", "")
                ltp = ltp_data.get(inst_key) or 0.0
                entry_price = ltp

                # Calculate SL
                current_sl_price = None
                if leg["sl_value"] > 0:
                    if leg["sl_type"] == "points":
                        current_sl_price = entry_price - leg["sl_value"] if leg["side"] == "BUY" else entry_price + leg["sl_value"]
                    elif leg["sl_type"] == "percentage":
                        current_sl_price = entry_price * (1 - leg["sl_value"] / 100) if leg["side"] == "BUY" else entry_price * (1 + leg["sl_value"] / 100)

                # Calculate Target
                current_target_price = None
                if leg["target_value"] > 0:
                    if leg["target_type"] == "points":
                        current_target_price = entry_price + leg["target_value"] if leg["side"] == "BUY" else entry_price - leg["target_value"]
                    elif leg["target_type"] == "percentage":
                        current_target_price = entry_price * (1 + leg["target_value"] / 100) if leg["side"] == "BUY" else entry_price * (1 - leg["target_value"] / 100)

                # Update Market leg
                await db.strategy_legs_collection.update_one(
                    {"_id": leg["_id"]},
                    {"$set": {
                        "entry_price": entry_price,
                        "current_sl_price": current_sl_price,
                        "current_target_price": current_target_price,
                        "current_status": "open",
                        "current_ltp": entry_price
                    }}
                )

                # Log Trade History for MARKET entries
                trade_doc = {
                    "_id": str(uuid.uuid4()),
                    "strategy_id": strat_id,
                    "leg_id": leg["_id"],
                    "user_id": strat["user_id"],
                    "action": leg["side"],
                    "symbol": leg.get("symbol", ""),
                    "strike": leg.get("strike", 0),
                    "option_type": leg.get("option_type", "CE"),
                    "price": entry_price,
                    "qty": leg.get("qty", 1),
                    "pnl": 0.0,
                    "exit_reason": "market_entry",
                    "timestamp": datetime.utcnow(),
                }
                await db.trade_history_collection.insert_one(trade_doc)

            # Mark strategy active
            await db.strategies_collection.update_one({"_id": strat_id}, {"$set": {"status": "active"}})
            logger.info(f"Auto-activated strategy {strat_id} at {current_hhmm}")

    async def _monitor_all_legs(self):
        """
        Core monitoring logic:
        1. Fetch all open & pending_entry legs across all users
        2. Batch-fetch LTP from Upstox
        3. Check each leg against SL/target or Limit Price
        4. Handle SL hit with move-SL-to-cost logic
        5. Push WebSocket updates
        """
        if db.strategy_legs_collection is None:
            return

        # 1. Get all open and pending_entry legs
        legs_cursor = db.strategy_legs_collection.find({"current_status": {"$in": ["open", "pending_entry"]}})
        open_legs = await legs_cursor.to_list(length=5000)

        if not open_legs:
            return

        # 2. Collect unique instrument keys and batch-fetch LTP
        instrument_keys = list(set(
            leg["instrument_key"]
            for leg in open_legs
            if leg.get("instrument_key")
        ))

        ltp_data = await fetch_ltp(instrument_keys) if instrument_keys else {}

        # 3. Process each leg
        # Group legs by strategy for move-SL-to-cost
        strategies_with_sl_hits = {}  # strategy_id -> [hit_leg_ids]

        for leg in open_legs:
            inst_key = leg.get("instrument_key", "")
            ltp = ltp_data.get(inst_key)

            if ltp is None:
                continue

            # Update current LTP in DB
            await db.strategy_legs_collection.update_one(
                {"_id": leg["_id"]},
                {"$set": {"current_ltp": ltp}},
            )

            side = leg["side"]
            strategy_id = leg["strategy_id"]

            # Handle LIMIT order entry
            if leg["current_status"] == "pending_entry":
                limit_price = leg.get("limit_price", 0.0)
                crossed = False
                if side == "BUY" and ltp <= limit_price:
                    crossed = True
                elif side == "SELL" and ltp >= limit_price:
                    crossed = True
                
                if crossed:
                    entry_price = ltp
                    
                    # Calculate SL
                    current_sl_price = None
                    if leg["sl_value"] > 0:
                        if leg["sl_type"] == "points":
                            current_sl_price = entry_price - leg["sl_value"] if side == "BUY" else entry_price + leg["sl_value"]
                        elif leg["sl_type"] == "percentage":
                            current_sl_price = entry_price * (1 - leg["sl_value"] / 100) if side == "BUY" else entry_price * (1 + leg["sl_value"] / 100)

                    # Calculate Target
                    current_target_price = None
                    if leg["target_value"] > 0:
                        if leg["target_type"] == "points":
                            current_target_price = entry_price + leg["target_value"] if side == "BUY" else entry_price - leg["target_value"]
                        elif leg["target_type"] == "percentage":
                            current_target_price = entry_price * (1 + leg["target_value"] / 100) if side == "BUY" else entry_price * (1 - leg["target_value"] / 100)
                    
                    await db.strategy_legs_collection.update_one(
                        {"_id": leg["_id"]},
                        {"$set": {
                            "entry_price": entry_price,
                            "current_sl_price": current_sl_price,
                            "current_target_price": current_target_price,
                            "current_status": "open"
                        }}
                    )

                    # Mark strategy active if draft (though limit orders usually active strategy)
                    await db.strategies_collection.update_one({"_id": strategy_id}, {"$set": {"status": "active"}})

                    # Log limit entry
                    strategy = await db.strategies_collection.find_one({"_id": strategy_id})
                    trade_doc = {
                        "_id": str(uuid.uuid4()),
                        "strategy_id": strategy_id,
                        "leg_id": leg["_id"],
                        "user_id": strategy["user_id"] if strategy else "",
                        "action": side,
                        "symbol": leg.get("symbol", ""),
                        "strike": leg.get("strike", 0),
                        "option_type": leg.get("option_type", "CE"),
                        "price": entry_price,
                        "qty": leg.get("qty", 1),
                        "pnl": 0.0,
                        "exit_reason": "limit_entry",
                        "timestamp": datetime.utcnow(),
                    }
                    await db.trade_history_collection.insert_one(trade_doc)
                    logger.info(f"LIMIT ENTRY: Leg {leg['_id']} triggered at {ltp}")
                
                # Wait for next tick to check SL/target
                continue

            entry_price = leg["entry_price"]
            if entry_price <= 0:
                continue

            sl_price = leg.get("current_sl_price")
            target_price = leg.get("current_target_price")

            # Check SL hit
            sl_hit = False
            if sl_price is not None:
                if side == "BUY" and ltp <= sl_price:
                    sl_hit = True
                elif side == "SELL" and ltp >= sl_price:
                    sl_hit = True

            # Check target hit
            target_hit = False
            if target_price is not None and not sl_hit:
                if side == "BUY" and ltp >= target_price:
                    target_hit = True
                elif side == "SELL" and ltp <= target_price:
                    target_hit = True

            if sl_hit:
                await self._close_leg(
                    leg, exit_price=ltp, reason="sl_hit", status="sl_hit"
                )
                # Track for move-SL-to-cost
                if strategy_id not in strategies_with_sl_hits:
                    strategies_with_sl_hits[strategy_id] = []
                strategies_with_sl_hits[strategy_id].append(leg["_id"])

                logger.info(
                    f"SL HIT: Leg {leg['_id']} ({leg.get('symbol')} "
                    f"{leg.get('strike')} {leg.get('option_type')} {side}) "
                    f"at {ltp} (SL was {sl_price})"
                )

            elif target_hit:
                await self._close_leg(
                    leg, exit_price=ltp, reason="target_hit", status="target_hit"
                )
                logger.info(
                    f"TARGET HIT: Leg {leg['_id']} ({leg.get('symbol')} "
                    f"{leg.get('strike')} {leg.get('option_type')} {side}) "
                    f"at {ltp} (Target was {target_price})"
                )

        # 4. Handle move-SL-to-cost for strategies that had SL hits
        for strategy_id, hit_leg_ids in strategies_with_sl_hits.items():
            await self._handle_move_sl_to_cost(strategy_id, hit_leg_ids)

        # 5. Check if any strategies should auto-close (all legs closed)
        await self._auto_close_strategies()

    async def _close_leg(self, leg: dict, exit_price: float, reason: str, status: str):
        """
        Close a leg: update status, calculate P&L, log trade history, update wallet.
        """
        entry = leg["entry_price"]
        lot_size = LOT_SIZES.get(leg.get("symbol", "NIFTY"), 50)
        total_qty = leg.get("qty", 1) * lot_size

        if leg["side"] == "BUY":
            realized_pnl = (exit_price - entry) * total_qty
        else:
            realized_pnl = (entry - exit_price) * total_qty

        # Update leg
        await db.strategy_legs_collection.update_one(
            {"_id": leg["_id"]},
            {"$set": {
                "current_status": status,
                "exit_price": exit_price,
                "exit_reason": reason,
                "current_ltp": exit_price,
            }},
        )

        # Get user_id from strategy
        strategy = await db.strategies_collection.find_one({"_id": leg["strategy_id"]})
        user_id = strategy["user_id"] if strategy else None

        # Log trade history
        trade_doc = {
            "_id": str(uuid.uuid4()),
            "strategy_id": leg["strategy_id"],
            "leg_id": leg["_id"],
            "user_id": user_id or "",
            "action": "SELL" if leg["side"] == "BUY" else "BUY",
            "symbol": leg.get("symbol", ""),
            "strike": leg.get("strike", 0),
            "option_type": leg.get("option_type", "CE"),
            "price": exit_price,
            "qty": leg.get("qty", 1),
            "pnl": round(realized_pnl, 2),
            "exit_reason": reason,
            "timestamp": datetime.utcnow(),
        }
        await db.trade_history_collection.insert_one(trade_doc)

        # Update wallet
        if user_id:
            await db.wallets_collection.update_one(
                {"user_id": user_id},
                {
                    "$inc": {"virtual_chips_balance": round(realized_pnl, 2)},
                    "$set": {"last_updated": datetime.utcnow()},
                },
            )

        # Push WebSocket notification
        if self._ws_manager and user_id:
            await self._ws_manager.send_to_user(user_id, {
                "type": reason,
                "strategy_id": leg["strategy_id"],
                "leg_id": leg["_id"],
                "exit_price": exit_price,
                "pnl": round(realized_pnl, 2),
                "symbol": leg.get("symbol", ""),
                "strike": leg.get("strike", 0),
                "option_type": leg.get("option_type", ""),
                "side": leg["side"],
            })

    async def _handle_move_sl_to_cost(self, strategy_id: str, hit_leg_ids: list):
        """
        When SL is hit on a strategy with move_sl_to_cost enabled:
        Move ALL OTHER open legs' SL to their own entry price (breakeven).
        """
        strategy = await db.strategies_collection.find_one({"_id": strategy_id})
        if not strategy or not strategy.get("move_sl_to_cost"):
            return

        # Find remaining open legs (excluding the ones that just hit SL)
        remaining_cursor = db.strategy_legs_collection.find({
            "strategy_id": strategy_id,
            "current_status": "open",
            "_id": {"$nin": hit_leg_ids},
        })
        remaining_legs = await remaining_cursor.to_list(length=20)

        if not remaining_legs:
            return

        affected_legs = []
        for leg in remaining_legs:
            entry_price = leg["entry_price"]
            # Move SL to entry price (cost) — breakeven protection
            await db.strategy_legs_collection.update_one(
                {"_id": leg["_id"]},
                {"$set": {
                    "current_sl_price": entry_price,
                    "sl_value": 0,
                    "sl_type": "points"
                }},
            )
            affected_legs.append({
                "leg_id": leg["_id"],
                "new_sl_price": entry_price,
                "symbol": leg.get("symbol", ""),
                "strike": leg.get("strike", 0),
                "option_type": leg.get("option_type", ""),
            })

        logger.info(
            f"MOVE SL TO COST: Strategy {strategy_id} — "
            f"updated {len(affected_legs)} remaining legs to breakeven SL"
        )

        # Push WebSocket notification
        if self._ws_manager and strategy.get("user_id"):
            await self._ws_manager.send_to_user(strategy["user_id"], {
                "type": "sl_moved_to_cost",
                "strategy_id": strategy_id,
                "affected_legs": affected_legs,
            })

    async def _auto_close_strategies(self):
        """Auto-close strategies where all legs are closed."""
        # Find active strategies
        cursor = db.strategies_collection.find({"status": "active"})
        active_strategies = await cursor.to_list(length=500)

        for strategy in active_strategies:
            open_count = await db.strategy_legs_collection.count_documents({
                "strategy_id": strategy["_id"],
                "current_status": "open",
            })
            if open_count == 0:
                await db.strategies_collection.update_one(
                    {"_id": strategy["_id"]},
                    {"$set": {"status": "closed", "closed_at": datetime.utcnow()}},
                )
                logger.info(f"Auto-closed strategy {strategy['_id']} — all legs exited.")


# Global singleton
monitor_service = MonitorService()
