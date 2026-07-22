"""
API endpoints for controlling the live/paper trading runner.
"""

from datetime import datetime
import uuid
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Body, WebSocket, WebSocketDisconnect

from live import db
from live.feed import feed_manager
from live.runner import runner_service
from config import DATA_DIR

router = APIRouter(prefix="/api/live", tags=["live"])


# Helper to get strategy config from JSON
def _get_strategy_config(strategy_id: str):
    strat_file = DATA_DIR / "saved_strategies.json"
    if strat_file.exists():
        with open(strat_file, "r") as f:
            strats = json.load(f)
            return strats.get(strategy_id)
    return None


@router.post("/deploy")
async def deploy_strategy(
    strategy_id: str = Body(...),
    mode: str = Body("paper"),
    max_daily_loss: float = Body(0.0),
    max_lots: int = Body(1),
    confirm: Optional[str] = Body(None)
):
    """Deploy a saved strategy to the paper runner.
    PAPER TRADE ONLY — live mode is structurally removed."""
    # PAPER TRADE ONLY: reject any non-paper mode
    if mode != "paper":
        raise HTTPException(400, "PAPER_TRADE_ONLY: Only 'paper' mode is supported. Live trading is structurally disabled.")
        
    config = _get_strategy_config(strategy_id)
    if not config:
        raise HTTPException(404, "Saved strategy not found.")
        
    user_id = "default_user"
    live_strat_id = str(uuid.uuid4())
    
    # Store deployed strategy
    deployed = {
        "_id": live_strat_id,
        "user_id": user_id,
        "strategy_id": strategy_id,
        "strategy_name": config.get("name", "Unknown Strategy"),
        "entry_time": config["config"].get("entry_time", "09:15:00"),
        "exit_time": config["config"].get("exit_time", "15:15:00"),
        "mode": "paper",  # Always paper
        "status": "waiting",
        "max_daily_loss": max_daily_loss,
        "max_lots": max_lots,
        "deployed_at": datetime.utcnow(),
    }
    await db.live_strategies_collection.insert_one(deployed)
    
    return {"status": "success", "live_strategy_id": live_strat_id}


@router.get("/deployed")
async def get_deployed_strategies():
    """List all deployed strategies (active and stopped)."""
    if db.live_strategies_collection is None:
        return []
    cursor = db.live_strategies_collection.find()
    strats = await cursor.to_list(length=100)
    return strats


@router.get("/{live_strategy_id}/status")
async def get_strategy_status(live_strategy_id: str):
    strat = await db.live_strategies_collection.find_one({"_id": live_strategy_id})
    if not strat:
        raise HTTPException(404, "Strategy not found")
        
    pos_cursor = db.live_positions_collection.find({"live_strategy_id": live_strategy_id})
    positions = await pos_cursor.to_list(length=100)
    
    return {
        "strategy": strat,
        "positions": positions
    }


@router.post("/{live_strategy_id}/kill")
async def kill_strategy(live_strategy_id: str):
    """Immediately square off all positions for this strategy."""
    strat = await db.live_strategies_collection.find_one({"_id": live_strategy_id})
    if not strat:
        raise HTTPException(404, "Strategy not found")
        
    await runner_service._kill_strategy(live_strategy_id, "USER_KILLED")
    return {"status": "success", "message": "Strategy killed and positions squared off."}


@router.post("/kill-all")
async def kill_all_strategies():
    """Global kill switch: square off ALL active/waiting strategies."""
    cursor = db.live_strategies_collection.find({"status": {"$in": ["active", "waiting"]}})
    active_strats = await cursor.to_list(length=100)
    
    for strat in active_strats:
        await runner_service._kill_strategy(strat["_id"], "GLOBAL_KILL_SWITCH")
        
    return {"status": "success", "message": f"Killed {len(active_strats)} active strategies."}


# ── WebSockets ─────────────────────────────────────────────────────────────

@router.websocket("/feed")
async def websocket_feed(websocket: WebSocket):
    """Streams live option chain and quote ticks."""
    await feed_manager.connect_client(websocket)
    try:
        while True:
            # Client can send messages to subscribe to specific instruments
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "subscribe" and msg.get("instrument"):
                    feed_manager.subscribe(msg["instrument"])
            except:
                pass
    except WebSocketDisconnect:
        feed_manager.disconnect_client(websocket)

# ── Wallet ─────────────────────────────────────────────────────────────
@router.get("/wallet")
async def get_wallet_balance():
    """Get the current paper trading wallet balance. Initialize to 250,000 if not exists."""
    wallet = await db.wallet_collection.find_one({"user_id": "default_user"})
    if not wallet:
        wallet = {"user_id": "default_user", "balance": 250000.0}
        await db.wallet_collection.insert_one(wallet)
        
    # Calculate unrealized PNL for open paper trading positions
    active_strats_cursor = db.live_strategies_collection.find({"mode": "paper", "status": "active"})
    active_strats = await active_strats_cursor.to_list(length=100)
    active_strat_ids = [s["_id"] for s in active_strats]

    unrealized_pnl = 0.0
    if active_strat_ids:
        positions_cursor = db.live_positions_collection.find(
            {"live_strategy_id": {"$in": active_strat_ids}, "status": "open"}
        )
        positions = await positions_cursor.to_list(length=1000)
        for pos in positions:
            unrealized_pnl += pos.get("unrealized_pnl", 0.0)

    net_worth = wallet["balance"] + unrealized_pnl

    return {
        "status": "success", 
        "balance": wallet["balance"],
        "unrealized_pnl": unrealized_pnl,
        "net_worth": net_worth
    }

@router.post("/wallet/reset")
async def reset_wallet_balance():
    """Reset the paper trading wallet balance to 250,000."""
    await db.wallet_collection.update_one(
        {"user_id": "default_user"},
        {"$set": {"balance": 250000.0}},
        upsert=True
    )
    return {"status": "success", "balance": 250000.0}
