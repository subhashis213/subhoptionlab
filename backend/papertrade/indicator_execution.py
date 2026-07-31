import logging
import uuid
import asyncio
from datetime import datetime
from papertrade import db
from papertrade.upstox_guard import fetch_quotes, build_instrument_key
from papertrade.router_markets import get_fallback_expiries
from data.stock_registry import get_lot_size
from papertrade.margin_calculator import compute_portfolio_margin
from papertrade.router_webhook import TradingViewPayload
from data.queries import resolve_atm_strike

logger = logging.getLogger(__name__)

async def process_webhook_signal(strategy: dict, payload: TradingViewPayload, log_id: str):
    """
    Background task to execute a TradingView signal.
    """
    try:
        # 1. Select the ATM strike based on index price
        underlying = payload.symbol.upper()
        if underlying not in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCAPNIFTY"]:
            raise ValueError(f"Unsupported symbol: {underlying}")
            
        atm_strike = resolve_atm_strike(underlying, payload.entry)
        
        # 2. Determine Option Type (CE for BUY, PE for SELL)
        option_type = "CE" if payload.action.upper() == "BUY" else "PE"
        
        # 3. Get Expiry (default to nearest)
        # We need a robust way to get expiry. For now, use the fallback logic to get the next thursday.
        expiries = get_fallback_expiries()
        expiry = expiries[0] # nearest
        
        # 4. Fetch Live Premium
        instrument_key = build_instrument_key(underlying, expiry, atm_strike, option_type)
        quotes = await fetch_quotes([instrument_key])
        if not quotes or instrument_key not in quotes:
            raise ValueError(f"Could not fetch live premium for {instrument_key}")
            
        live_premium = quotes[instrument_key].get("ltp", 0.0)
        if live_premium <= 0:
            raise ValueError(f"Invalid live premium {live_premium} for {instrument_key}")
            
        # 5. Margin Check (We are BUYING options, margin is Premium * Lot Size)
        lot_size = get_lot_size(underlying)
        # default to 1 lot for auto-execution, could make this configurable
        qty = 1 * lot_size
        required_margin = live_premium * qty
        
        # Fetch user wallet
        user_id = strategy["user_id"]
        wallet = await db.wallets_collection.find_one({"user_id": user_id})
        available_margin = wallet.get("balance", 0.0)
        
        if available_margin < required_margin:
            raise ValueError(f"Insufficient margin. Required: {required_margin}, Available: {available_margin}")
            
        # 6. Ladder Calculation
        multiplier = float(strategy.get("ladder_multiplier", 0.5))
        
        # R = Entry - SL
        # If BUY (CE), index is expected to go up. SL is below entry.
        # If SELL (PE), index is expected to go down. SL is above entry.
        # Using abs() ensures R is positive.
        index_r = abs(payload.entry - payload.sl)
        option_r = index_r * multiplier
        
        # For option buyers (CE or PE), we always want the premium to go UP.
        # SL is always entry_price - option_r
        # Targets are entry_price + (0.4 * option_r), etc.
        option_sl = live_premium - option_r
        if option_sl < 0.05:
            option_sl = 0.05 # floor at 0.05
            
        # We'll use Level 1 as the primary target for the leg? The user mentioned 5 levels.
        # Let's set the target to Level 5, and we'll log the other levels or we could create 5 legs (1 lot each).
        # "manage SL/target dynamically" - maybe the user wants multiple legs or just 1 leg with Lvl 1?
        # For now, let's set the target to Lvl 5.
        target_value = option_r * 2.50
        
        # 7. Create Strategy Leg
        leg_id = str(uuid.uuid4())
        leg_doc = {
            "_id": leg_id,
            "strategy_id": str(strategy["_id"]),
            "symbol": underlying,
            "expiry": expiry,
            "strike": atm_strike,
            "option_type": option_type,
            "side": "BUY",
            "qty": qty,
            "order_type": "MARKET",
            "limit_price": 0.0,
            "entry_price": live_premium, # We execute instantly
            "sl_type": "points",
            "sl_value": live_premium - option_sl, # points distance
            "target_type": "points",
            "target_value": target_value, # points distance
            "current_sl_price": option_sl,
            "current_target_price": live_premium + target_value,
            "current_status": "open",
            "current_ltp": live_premium,
            "exit_price": None,
            "exit_reason": None,
            "instrument_key": instrument_key,
            "created_at": datetime.utcnow(),
            "webhook_log_id": log_id, # Link back to the log
        }
        
        # Insert leg
        await db.strategy_legs_collection.insert_one(leg_doc)
        
        # Update strategy status to active if it was pending/draft
        if strategy.get("status") in ["draft", "pending"]:
            await db.strategies_collection.update_one(
                {"_id": strategy["_id"]},
                {"$set": {"status": "active"}}
            )
            
        # Deduct margin
        await db.wallets_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": -required_margin}}
        )
        
        # Add wallet transaction
        txn = {
            "user_id": user_id,
            "amount": -required_margin,
            "type": "debit",
            "description": f"Margin blocked for auto-executed webhook leg {leg_id}",
            "created_at": datetime.utcnow(),
            "reference_id": leg_id
        }
        await db.chip_transactions_collection.insert_one(txn)
        
        # Mark log as SUCCESS
        await db.webhook_logs_collection.update_one(
            {"_id": log_id},
            {"$set": {"status": "EXECUTED", "reason": f"Executed on {instrument_key} @ {live_premium}"}}
        )
        logger.info(f"Webhook {log_id} successfully executed for {instrument_key}")
        
    except Exception as e:
        logger.error(f"Error processing webhook {log_id}: {e}")
        await db.webhook_logs_collection.update_one(
            {"_id": log_id},
            {"$set": {"status": "FAILED", "reason": str(e)}}
        )
