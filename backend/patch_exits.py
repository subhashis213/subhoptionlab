import re

content = open("/Users/subhashis/Desktop/backtest/backend/papertrade/monitor.py").read()

new_loop_body = """    async def _run_loop(self):
        \"\"\"Main polling loop — every 3 seconds during market hours.\"\"\"
        while self._running:
            try:
                if self._is_market_hours():
                    await self._monitor_pending_strategies()
                    await self._monitor_all_legs()
                    await self._monitor_exits()
                else:
                    logger.debug("Outside market hours, monitor sleeping...")
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)

            await asyncio.sleep(3)"""

new_monitor_exits = """    async def _monitor_exits(self):
        \"\"\"Check 'active' strategies and exit all open legs if exit_time is met.\"\"\"
        if db.strategies_collection is None:
            return

        now_ist = datetime.now(IST)
        current_hhmm = now_ist.strftime("%H:%M")

        # Find active strategies where exit_time <= current time
        exit_cursor = db.strategies_collection.find({
            "status": "active",
            "exit_time": {"$lte": current_hhmm, "$ne": None}
        })
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
                await db.strategies_collection.update_one({"_id": strat_id}, {"$set": {"status": "closed", "closed_at": datetime.utcnow()}})
                continue

            # Fetch LTP for closing
            instrument_keys = [leg["instrument_key"] for leg in open_legs if leg.get("instrument_key")]
            ltp_data = await fetch_ltp(instrument_keys) if instrument_keys else {}

            for leg in open_legs:
                inst_key = leg.get("instrument_key", "")
                exit_price = ltp_data.get(inst_key)
                
                if exit_price is None:
                    continue  # Can't exit without price
                    
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
                        "exit_reason": "time_exit",
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
                    "exit_reason": "time_exit",
                    "timestamp": datetime.utcnow(),
                }
                await db.trade_history_collection.insert_one(trade_doc)

            # Close strategy
            await db.strategies_collection.update_one({"_id": strat_id}, {"$set": {"status": "closed", "closed_at": datetime.utcnow()}})
            logger.info(f"Auto-closed strategy {strat_id} at {current_hhmm}")"""

start_idx = content.find("    async def _run_loop(self):")
end_idx = content.find("    async def _monitor_pending_strategies(self):")

content = content[:start_idx] + new_loop_body + "\n\n" + new_monitor_exits + "\n\n" + content[end_idx:]

with open("/Users/subhashis/Desktop/backtest/backend/papertrade/monitor.py", "w") as f:
    f.write(content)
