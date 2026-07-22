import re

content = open("/Users/subhashis/Desktop/backtest/backend/papertrade/monitor.py").read()

new_imports = """
from papertrade.upstox_guard import fetch_ltp, build_instrument_key
from papertrade.router_markets import INDICES
from config import LOT_SIZES
import re
"""

content = content.replace("from papertrade.upstox_guard import fetch_ltp\nfrom config import LOT_SIZES", new_imports.strip())

new_pending_method = """    async def _monitor_pending_strategies(self):
        \"\"\"Check 'pending' strategies and activate if entry_time is met.\"\"\"
        if db.strategies_collection is None:
            return

        now_ist = datetime.now(IST)
        current_hhmm = now_ist.strftime("%H:%M")

        # Find pending strategies where entry_time <= current time
        pending_cursor = db.strategies_collection.find({
            "status": "pending",
            "entry_time": {"$lte": current_hhmm, "$ne": None}
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
                if leg.get("instrument_key") is None:
                    strike_val = leg.get("strike")
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
                            match = re.match(r"(ITM|OTM)(\\d+)", strike_val)
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
            logger.info(f"Auto-activated strategy {strat_id} at {current_hhmm}")"""

# find start and end of _monitor_pending_strategies
import re
start_idx = content.find("    async def _monitor_pending_strategies(self):")
end_idx = content.find("    async def _monitor_all_legs(self):")

content = content[:start_idx] + new_pending_method + "\n\n" + content[end_idx:]

with open("/Users/subhashis/Desktop/backtest/backend/papertrade/monitor.py", "w") as f:
    f.write(content)

