"""
Strategy + Leg CRUD API endpoints for paper trading users.
Handles strategy creation, activation (fetches live LTP), manual exits, and closing.
"""

import uuid
import logging
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from papertrade import db
from papertrade.auth import require_user
from papertrade.models import StrategyCreate, StrategyResponse
from papertrade.upstox_guard import fetch_ltp, build_instrument_key, resolve_instrument_keys
from papertrade.router_markets import INDICES
from config import LOT_SIZES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pt/strategies", tags=["strategies"])


# ── Create Strategy ────────────────────────────────────────────────────────────

@router.post("/")
async def create_strategy(req: StrategyCreate, user: dict = Depends(require_user)):
    """Create a new paper trading strategy with multiple legs (draft status)."""
    user_id = user["_id"]
    strategy_id = str(uuid.uuid4())

    # Create strategy document
    strategy_doc = {
        "_id": strategy_id,
        "user_id": user_id,
        "name": req.name.strip(),
        "underlying": req.underlying,
        "move_sl_to_cost": req.move_sl_to_cost,
        "status": "pending" if req.entry_time else "draft",
        "entry_time": req.entry_time if req.entry_time else None,
        "exit_time": req.exit_time if req.exit_time else None,
        "created_at": datetime.utcnow(),
        "closed_at": None,
    }
    await db.strategies_collection.insert_one(strategy_doc)

    # Create leg documents
    legs = []
    for leg_data in req.legs:
        leg_id = str(uuid.uuid4())

        # Build instrument key for Upstox quote fetching (only if strike is fixed number)
        instrument_key = getattr(leg_data, 'instrument_key', None)
        if not instrument_key:
            try:
                strike_float = float(leg_data.strike)
                instrument_key = build_instrument_key(
                    underlying=leg_data.symbol or req.underlying,
                    expiry=leg_data.expiry,
                    strike=strike_float,
                    option_type=leg_data.option_type,
                )
            except ValueError:
                # It's a dynamic strike like "ATM", "ITM1"
                pass

        leg_doc = {
            "_id": leg_id,
            "strategy_id": strategy_id,
            "symbol": leg_data.symbol or req.underlying,
            "expiry": leg_data.expiry,
            "strike": leg_data.strike,
            "option_type": leg_data.option_type,
            "side": leg_data.side,
            "qty": leg_data.qty,
            "order_type": leg_data.order_type,
            "limit_price": leg_data.limit_price,
            "entry_price": 0.0,  # Set on activation or limit hit
            "sl_type": leg_data.sl_type,
            "sl_value": leg_data.sl_value,
            "target_type": leg_data.target_type,
            "target_value": leg_data.target_value,
            "current_sl_price": None,
            "current_target_price": None,
            "current_status": "pending_entry" if leg_data.order_type == "LIMIT" else "open",
            "current_ltp": 0.0,
            "exit_price": None,
            "exit_reason": None,
            "instrument_key": instrument_key,
            "created_at": datetime.utcnow(),
        }
        legs.append(leg_doc)

    if legs:
        await resolve_instrument_keys(legs)
        await db.strategy_legs_collection.insert_many(legs)

    return {
        "status": "success",
        "strategy_id": strategy_id,
        "legs_created": len(legs),
    }


# ── List Strategies ────────────────────────────────────────────────────────────

@router.get("/")
async def list_strategies(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_user),
):
    """List user's strategies with optional status filter."""
    query = {"user_id": user["_id"]}
    if status_filter:
        query["status"] = status_filter

    cursor = (
        db.strategies_collection
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    strategies = await cursor.to_list(length=limit)
    total = await db.strategies_collection.count_documents(query)

    # Attach legs and P&L summary to each strategy
    result = []
    for s in strategies:
        legs_cursor = db.strategy_legs_collection.find({"strategy_id": s["_id"]})
        legs = await legs_cursor.to_list(length=20)

        total_pnl = 0.0
        for leg in legs:
            entry = leg.get("entry_price", 0)
            current = leg.get("current_ltp", entry)
            lot_size = LOT_SIZES.get(leg.get("symbol", "NIFTY"), 50)
            total_qty = leg.get("qty", 1) * lot_size

            if leg["current_status"] in ("sl_hit", "target_hit", "manually_closed"):
                # Use realized P&L
                exit_p = leg.get("exit_price", entry)
                if leg["side"] == "BUY":
                    total_pnl += (exit_p - entry) * total_qty
                else:
                    total_pnl += (entry - exit_p) * total_qty
            elif leg["current_status"] == "open" and entry > 0:
                # Unrealized P&L
                if leg["side"] == "BUY":
                    total_pnl += (current - entry) * total_qty
                else:
                    total_pnl += (entry - current) * total_qty

        result.append({
            **s,
            "legs": legs,
            "total_pnl": round(total_pnl, 2),
            "open_legs": sum(1 for l in legs if l["current_status"] == "open"),
            "total_legs": len(legs),
        })

    return {"strategies": result, "total": total}


# ── Get Strategy Detail ───────────────────────────────────────────────────────

@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str, user: dict = Depends(require_user)):
    """Get a strategy with all legs and live price data."""
    strategy = await db.strategies_collection.find_one({
        "_id": strategy_id,
        "user_id": user["_id"],
    })
    if not strategy:
        raise HTTPException(404, "Strategy not found")

    legs_cursor = db.strategy_legs_collection.find({"strategy_id": strategy_id})
    legs = await legs_cursor.to_list(length=20)

    # Calculate P&L for each leg
    total_pnl = 0.0
    for leg in legs:
        entry = leg.get("entry_price", 0)
        lot_size = LOT_SIZES.get(leg.get("symbol", "NIFTY"), 50)
        total_qty = leg.get("qty", 1) * lot_size

        if leg["current_status"] in ("sl_hit", "target_hit", "manually_closed"):
            exit_p = leg.get("exit_price", entry)
            if leg["side"] == "BUY":
                leg["realized_pnl"] = round((exit_p - entry) * total_qty, 2)
            else:
                leg["realized_pnl"] = round((entry - exit_p) * total_qty, 2)
            total_pnl += leg["realized_pnl"]
        elif leg["current_status"] == "open" and entry > 0:
            current = leg.get("current_ltp", entry)
            if leg["side"] == "BUY":
                leg["unrealized_pnl"] = round((current - entry) * total_qty, 2)
            else:
                leg["unrealized_pnl"] = round((entry - current) * total_qty, 2)
            total_pnl += leg.get("unrealized_pnl", 0)

    return {
        **strategy,
        "legs": legs,
        "total_pnl": round(total_pnl, 2),
    }


# ── Activate Strategy ──────────────────────────────────────────────────────────

@router.post("/{strategy_id}/activate")
async def activate_strategy(strategy_id: str, user: dict = Depends(require_user)):
    """
    Activate a draft strategy:
    1. Fetch live LTP for each leg from Upstox
    2. Set entry_price = LTP
    3. Calculate SL/target prices from entry + sl_value/target_value
    4. Set status = active
    """
    strategy = await db.strategies_collection.find_one({
        "_id": strategy_id,
        "user_id": user["_id"],
    })
    if not strategy:
        raise HTTPException(404, "Strategy not found")

    if strategy["status"] != "draft":
        raise HTTPException(400, f"Strategy is already {strategy['status']}")

    # Get all legs
    legs_cursor = db.strategy_legs_collection.find({"strategy_id": strategy_id})
    legs = await legs_cursor.to_list(length=20)

    if not legs:
        raise HTTPException(400, "Strategy has no legs")

    # 1. Resolve dynamic strikes (ATM/ITM/OTM)
    keys = list(INDICES.values())
    index_quotes = await fetch_ltp(keys)

    for leg in legs:
        strike_val = leg.get("strike")
        if leg.get("instrument_key") is None or isinstance(strike_val, str):
            underlying = leg.get("symbol", strategy.get("underlying"))
            option_type = leg.get("option_type", "CE")
            index_key = INDICES.get(underlying)
            spot_price = index_quotes.get(index_key, 0.0) if index_key else 0.0
            if spot_price <= 0:
                defaults = {"NIFTY": 24180.6, "BANKNIFTY": 57968.6, "FINNIFTY": 23500.0, "MIDCAPNIFTY": 12500.0}
                spot_price = defaults.get(underlying, 24180.6)
            
            steps = {"NIFTY": 50, "BANKNIFTY": 100, "FINNIFTY": 50, "MIDCAPNIFTY": 25}
            step = steps.get(underlying, 50)
            atm = round(spot_price / step) * step
            resolved_strike = atm
            
            
            if isinstance(strike_val, str):
                match = re.match(r"^(ITM|OTM)(\d+)$", strike_val.upper().strip())
                if match:
                    type_ = match.group(1)
                    offset = int(match.group(2))
                    if option_type == "CE":
                        resolved_strike = atm - (offset * step) if type_ == "ITM" else atm + (offset * step)
                    else:
                        resolved_strike = atm + (offset * step) if type_ == "ITM" else atm - (offset * step)
                elif strike_val.upper().strip() == "ATM":
                    resolved_strike = atm
            else:
                resolved_strike = float(strike_val)

            leg["strike"] = resolved_strike
            leg["instrument_key"] = build_instrument_key(underlying, leg["expiry"], resolved_strike, option_type)
            
            # Update DB
            await db.strategy_legs_collection.update_one(
                {"_id": leg["_id"]},
                {"$set": {"strike": resolved_strike, "instrument_key": leg["instrument_key"]}}
            )

    # Collect all instrument keys and batch-fetch LTP
    instrument_keys = [leg["instrument_key"] for leg in legs if leg.get("instrument_key")]
    ltp_data = await fetch_ltp(instrument_keys) if instrument_keys else {}

    # Update each leg with entry price and SL/target calculations
    for leg in legs:
        inst_key = leg.get("instrument_key", "")
        ltp = ltp_data.get(inst_key)

        if ltp is None or ltp <= 0:
            # If we can't get live price, use a fallback or reject
            logger.warning(f"No LTP for {inst_key}, using 0. Strategy may need manual entry price.")
            ltp = 0.0

        entry_price = ltp

        # Calculate SL price (calculated ONCE from entry, stored as absolute)
        current_sl_price = None
        if leg["sl_value"] > 0:
            if leg["sl_type"] == "points":
                if leg["side"] == "BUY":
                    current_sl_price = entry_price - leg["sl_value"]
                else:
                    current_sl_price = entry_price + leg["sl_value"]
            elif leg["sl_type"] == "percentage":
                if leg["side"] == "BUY":
                    current_sl_price = entry_price * (1 - leg["sl_value"] / 100)
                else:
                    current_sl_price = entry_price * (1 + leg["sl_value"] / 100)

        # Calculate target price
        current_target_price = None
        if leg["target_value"] > 0:
            if leg["target_type"] == "points":
                if leg["side"] == "BUY":
                    current_target_price = entry_price + leg["target_value"]
                else:
                    current_target_price = entry_price - leg["target_value"]
            elif leg["target_type"] == "percentage":
                if leg["side"] == "BUY":
                    current_target_price = entry_price * (1 + leg["target_value"] / 100)
                else:
                    current_target_price = entry_price * (1 - leg["target_value"] / 100)

        await db.strategy_legs_collection.update_one(
            {"_id": leg["_id"]},
            {"$set": {
                "entry_price": entry_price,
                "current_ltp": entry_price,
                "current_status": "open",
                "current_sl_price": round(current_sl_price, 2) if current_sl_price else None,
                "current_target_price": round(current_target_price, 2) if current_target_price else None,
            }},
        )

    # Update strategy status
    await db.strategies_collection.update_one(
        {"_id": strategy_id},
        {"$set": {"status": "active"}},
    )

    return {
        "status": "success",
        "message": "Strategy activated with live entry prices",
        "strategy_id": strategy_id,
        "legs_activated": len(legs),
    }


# ── Manual Exit Leg ────────────────────────────────────────────────────────────

@router.post("/{strategy_id}/legs/{leg_id}/exit")
async def exit_leg(strategy_id: str, leg_id: str, user: dict = Depends(require_user)):
    """Manually exit a single open leg."""
    strategy = await db.strategies_collection.find_one({
        "_id": strategy_id,
        "user_id": user["_id"],
    })
    if not strategy:
        raise HTTPException(404, "Strategy not found")

    leg = await db.strategy_legs_collection.find_one({
        "_id": leg_id,
        "strategy_id": strategy_id,
    })
    if not leg:
        raise HTTPException(404, "Leg not found")

    if leg["current_status"] != "open":
        raise HTTPException(400, f"Leg is already {leg['current_status']}")

    # Get current LTP for exit price
    exit_price = leg.get("current_ltp", leg.get("entry_price", 0))
    if leg.get("instrument_key"):
        ltp_data = await fetch_ltp([leg["instrument_key"]])
        if ltp_data:
            exit_price = ltp_data.get(leg["instrument_key"], exit_price)

    # Calculate realized P&L
    entry = leg["entry_price"]
    lot_size = LOT_SIZES.get(leg.get("symbol", "NIFTY"), 50)
    total_qty = leg.get("qty", 1) * lot_size

    if leg["side"] == "BUY":
        realized_pnl = (exit_price - entry) * total_qty
    else:
        realized_pnl = (entry - exit_price) * total_qty

    # Update leg
    await db.strategy_legs_collection.update_one(
        {"_id": leg_id},
        {"$set": {
            "current_status": "manually_closed",
            "exit_price": exit_price,
            "exit_reason": "manual_exit",
            "current_ltp": exit_price,
        }},
    )

    # Log trade history
    trade_doc = {
        "_id": str(uuid.uuid4()),
        "strategy_id": strategy_id,
        "leg_id": leg_id,
        "user_id": user["_id"],
        "action": "SELL" if leg["side"] == "BUY" else "BUY",
        "symbol": leg.get("symbol", ""),
        "strike": leg.get("strike", 0),
        "option_type": leg.get("option_type", "CE"),
        "price": exit_price,
        "qty": leg.get("qty", 1),
        "pnl": round(realized_pnl, 2),
        "exit_reason": "manual_exit",
        "timestamp": datetime.utcnow(),
    }
    await db.trade_history_collection.insert_one(trade_doc)

    # Update wallet with realized P&L
    await db.wallets_collection.update_one(
        {"user_id": user["_id"]},
        {
            "$inc": {"virtual_chips_balance": round(realized_pnl, 2)},
            "$set": {"last_updated": datetime.utcnow()},
        },
    )

    # Check if all legs are closed — if so, close the strategy
    open_count = await db.strategy_legs_collection.count_documents({
        "strategy_id": strategy_id,
        "current_status": "open",
    })
    if open_count == 0:
        await db.strategies_collection.update_one(
            {"_id": strategy_id},
            {"$set": {"status": "closed", "closed_at": datetime.utcnow()}},
        )

    return {
        "status": "success",
        "leg_id": leg_id,
        "exit_price": exit_price,
        "realized_pnl": round(realized_pnl, 2),
    }


# ── Exit All Legs ──────────────────────────────────────────────────────────────

@router.post("/{strategy_id}/exit-all")
async def exit_all_legs(strategy_id: str, user: dict = Depends(require_user)):
    """Exit all open legs in a strategy."""
    strategy = await db.strategies_collection.find_one({
        "_id": strategy_id,
        "user_id": user["_id"],
    })
    if not strategy:
        raise HTTPException(404, "Strategy not found")

    # Find all open legs
    legs_cursor = db.strategy_legs_collection.find({
        "strategy_id": strategy_id,
        "current_status": "open",
    })
    open_legs = await legs_cursor.to_list(length=20)

    if not open_legs:
        raise HTTPException(400, "No open legs to exit")

    # Batch fetch LTP
    instrument_keys = [l["instrument_key"] for l in open_legs if l.get("instrument_key")]
    ltp_data = await fetch_ltp(instrument_keys) if instrument_keys else {}

    total_pnl = 0.0
    closed_legs = []

    for leg in open_legs:
        exit_price = ltp_data.get(leg.get("instrument_key", ""), leg.get("current_ltp", leg["entry_price"]))
        entry = leg["entry_price"]
        lot_size = LOT_SIZES.get(leg.get("symbol", "NIFTY"), 50)
        total_qty = leg.get("qty", 1) * lot_size

        if leg["side"] == "BUY":
            pnl = (exit_price - entry) * total_qty
        else:
            pnl = (entry - exit_price) * total_qty

        total_pnl += pnl

        await db.strategy_legs_collection.update_one(
            {"_id": leg["_id"]},
            {"$set": {
                "current_status": "manually_closed",
                "exit_price": exit_price,
                "exit_reason": "exit_all",
                "current_ltp": exit_price,
            }},
        )

        # Log trade
        await db.trade_history_collection.insert_one({
            "_id": str(uuid.uuid4()),
            "strategy_id": strategy_id,
            "leg_id": leg["_id"],
            "user_id": user["_id"],
            "action": "SELL" if leg["side"] == "BUY" else "BUY",
            "symbol": leg.get("symbol", ""),
            "strike": leg.get("strike", 0),
            "option_type": leg.get("option_type", "CE"),
            "price": exit_price,
            "qty": leg.get("qty", 1),
            "pnl": round(pnl, 2),
            "exit_reason": "exit_all",
            "timestamp": datetime.utcnow(),
        })

        closed_legs.append({"leg_id": leg["_id"], "exit_price": exit_price, "pnl": round(pnl, 2)})

    # Update wallet
    await db.wallets_collection.update_one(
        {"user_id": user["_id"]},
        {
            "$inc": {"virtual_chips_balance": round(total_pnl, 2)},
            "$set": {"last_updated": datetime.utcnow()},
        },
    )

    # Close strategy
    await db.strategies_collection.update_one(
        {"_id": strategy_id},
        {"$set": {"status": "closed", "closed_at": datetime.utcnow()}},
    )

    return {
        "status": "success",
        "strategy_id": strategy_id,
        "closed_legs": closed_legs,
        "total_pnl": round(total_pnl, 2),
    }


# ── Close Strategy ─────────────────────────────────────────────────────────────

@router.post("/{strategy_id}/close")
async def close_strategy(strategy_id: str, user: dict = Depends(require_user)):
    """Mark a strategy as closed (only if all legs are already closed)."""
    strategy = await db.strategies_collection.find_one({
        "_id": strategy_id,
        "user_id": user["_id"],
    })
    if not strategy:
        raise HTTPException(404, "Strategy not found")

    open_count = await db.strategy_legs_collection.count_documents({
        "strategy_id": strategy_id,
        "current_status": "open",
    })
    if open_count > 0:
        raise HTTPException(400, f"Cannot close — {open_count} legs still open. Use exit-all first.")

    await db.strategies_collection.update_one(
        {"_id": strategy_id},
        {"$set": {"status": "closed", "closed_at": datetime.utcnow()}},
    )

    return {"status": "success", "strategy_id": strategy_id}


# ── Reuse Strategy ─────────────────────────────────────────────────────────────

@router.post("/{strategy_id}/reuse")
async def reuse_strategy(strategy_id: str, user: dict = Depends(require_user)):
    """Clone a closed strategy and set it to draft/pending for reuse today."""
    strategy = await db.strategies_collection.find_one({
        "_id": strategy_id,
        "user_id": user["_id"],
    })
    if not strategy:
        raise HTTPException(404, "Strategy not found")

    legs_cursor = db.strategy_legs_collection.find({"strategy_id": strategy_id})
    legs = await legs_cursor.to_list(length=20)

    new_strategy_id = str(uuid.uuid4())
    
    # Check if entry_time is already passed today. If so, it might activate immediately 
    # when we call activate endpoint. But we just create it as pending/draft here.
    status = "pending" if strategy.get("entry_time") else "draft"

    new_strategy = {
        "_id": new_strategy_id,
        "user_id": user["_id"],
        "name": f"{strategy['name']} (Copy)",
        "underlying": strategy["underlying"],
        "move_sl_to_cost": strategy.get("move_sl_to_cost", False),
        "status": status,
        "entry_time": strategy.get("entry_time"),
        "exit_time": strategy.get("exit_time"),
        "created_at": datetime.utcnow(),
        "closed_at": None,
    }
    await db.strategies_collection.insert_one(new_strategy)

    # We use "current_month" so that resolve_instrument_keys dynamically 
    # fetches the true current active expiry for the copied strategy.
    next_expiry = "current_month"

    new_legs = []
    for leg in legs:
        leg_id = str(uuid.uuid4())
        
        # Build instrument key only if strike is numeric
        instrument_key = None
        try:
            strike_float = float(leg["strike"])
            instrument_key = build_instrument_key(
                underlying=leg["symbol"],
                expiry=next_expiry,
                strike=strike_float,
                option_type=leg["option_type"],
            )
        except ValueError:
            pass
            
        new_leg = {
            "_id": leg_id,
            "strategy_id": new_strategy_id,
            "symbol": leg["symbol"],
            "expiry": next_expiry,  # Auto-update expiry
            "strike": leg["strike"],
            "option_type": leg["option_type"],
            "side": leg["side"],
            "qty": leg["qty"],
            "order_type": leg.get("order_type", "MARKET"),
            "limit_price": leg.get("limit_price", 0.0),
            "entry_price": 0.0,
            "sl_type": leg["sl_type"],
            "sl_value": leg["sl_value"],
            "target_type": leg["target_type"],
            "target_value": leg["target_value"],
            "current_sl_price": None,
            "current_target_price": None,
            "current_status": "pending_entry" if leg.get("order_type") == "LIMIT" else "open",
            "current_ltp": 0.0,
            "exit_price": None,
            "exit_reason": None,
            "instrument_key": instrument_key,
            "created_at": datetime.utcnow(),
        }
        new_legs.append(new_leg)

    if new_legs:
        await resolve_instrument_keys(new_legs)
        await db.strategy_legs_collection.insert_many(new_legs)

    return {
        "status": "success",
        "new_strategy_id": new_strategy_id,
        "legs_cloned": len(new_legs),
    }

# ── Delete Strategy ────────────────────────────────────────────────────────────

@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: str, user: dict = Depends(require_user)):
    """Delete a strategy and its legs. Only allowed if not active."""
    strategy = await db.strategies_collection.find_one({
        "_id": strategy_id,
        "user_id": user["_id"],
    })
    if not strategy:
        raise HTTPException(404, "Strategy not found")
        
    if strategy.get("status") == "active":
        raise HTTPException(400, "Cannot delete an active strategy. Close it first.")

    await db.strategies_collection.delete_one({"_id": strategy_id})
    await db.strategy_legs_collection.delete_many({"strategy_id": strategy_id})

    return {"status": "success", "message": "Strategy deleted successfully"}

# ── Update Strategy Times ──────────────────────────────────────────────────────

class UpdateTimesRequest(BaseModel):
    start_time: str
    end_time: str

@router.put("/{strategy_id}/times")
async def update_strategy_times(
    strategy_id: str,
    req: UpdateTimesRequest,
    user: dict = Depends(require_user)
):
    """Update start_time and end_time of a pending/draft strategy."""
    strategy = await db.strategies_collection.find_one({
        "_id": strategy_id,
        "user_id": user["_id"],
    })
    if not strategy:
        raise HTTPException(404, "Strategy not found")
        
    if strategy.get("status") not in ("draft", "pending"):
        raise HTTPException(400, "Can only update times for draft or pending strategies")

    await db.strategies_collection.update_one(
        {"_id": strategy_id},
        {"$set": {
            "start_time": req.start_time,
            "end_time": req.end_time
        }}
    )

    return {"status": "success", "message": "Strategy times updated successfully"}
