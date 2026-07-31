import logging
import asyncio
import hashlib
from datetime import datetime
from typing import Optional, Literal
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field

from papertrade import db
from papertrade.models import WebhookLogInDB
from papertrade.indicator_execution import process_webhook_signal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

class TradingViewPayload(BaseModel):
    token: str
    strategy_id: str
    symbol: str
    timeframe: str
    action: Literal["BUY", "SELL"]
    entry: float
    sl: Optional[float] = None
    time: str


@router.post("/tradingview")
async def tradingview_webhook(payload: TradingViewPayload, background_tasks: BackgroundTasks, request: Request):
    """
    Receive webhook signals from TradingView.
    Respond within 3 seconds and offload actual execution to background task.
    """
    raw_body = await request.json()
    
    # 1. Fetch strategy and validate token
    strategy = await db.strategies_collection.find_one({"_id": payload.strategy_id})
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
        
    if not strategy.get("webhook_enabled"):
        await _log_webhook(payload, raw_body, strategy, "LOGGED_ONLY", "Webhook is disabled for this strategy")
        return {"status": "logged", "reason": "webhook_disabled"}
        
    if payload.token != strategy.get("webhook_secret"):
        await _log_webhook(payload, raw_body, strategy, "REJECTED", "Invalid webhook secret token")
        raise HTTPException(status_code=401, detail="Unauthorized token")
        
    # 2. Check timeframe
    accepted_timeframes = strategy.get("accepted_timeframes", [])
    if accepted_timeframes and payload.timeframe not in accepted_timeframes:
        await _log_webhook(payload, raw_body, strategy, "LOGGED_ONLY", f"Timeframe {payload.timeframe} not in accepted list")
        return {"status": "logged", "reason": "timeframe_mismatch"}
        
    # 3. Duplicate check (symbol + time + strategy_id)
    dup_hash = hashlib.sha256(f"{payload.strategy_id}_{payload.symbol}_{payload.time}".encode()).hexdigest()
    
    existing = await db.webhook_logs_collection.find_one({
        "strategy_id": payload.strategy_id,
        "symbol": payload.symbol,
        "signal_time": payload.time
    })
    
    if existing:
        return {"status": "rejected", "reason": "duplicate_signal"}
        
    # 4. Check if SL is missing
    if payload.sl is None or payload.sl <= 0:
        await _log_webhook(payload, raw_body, strategy, "REJECTED", "SL_UNAVAILABLE")
        return {"status": "rejected", "reason": "sl_unavailable"}
        
    # 5. All checks passed, offload to background
    log_doc = await _log_webhook(payload, raw_body, strategy, "EXECUTED", "Signal accepted and queued for execution")
    
    background_tasks.add_task(process_webhook_signal, strategy, payload, log_doc["_id"])
    
    return {"status": "accepted"}


async def _log_webhook(payload: TradingViewPayload, raw: dict, strategy: dict, status: str, reason: str = None):
    doc = WebhookLogInDB(
        strategy_id=payload.strategy_id,
        user_id=strategy.get("user_id"),
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        action=payload.action,
        entry_price=payload.entry,
        sl_price=payload.sl,
        signal_time=payload.time,
        status=status,
        reason=reason,
        raw_payload=raw
    )
    doc_dict = doc.model_dump(by_alias=True)
    await db.webhook_logs_collection.insert_one(doc_dict)
    return doc_dict

from papertrade.auth import require_user
from fastapi import Depends

@router.get("/logs/{strategy_id}")
async def get_webhook_logs(strategy_id: str, user: dict = Depends(require_user)):
    """Fetch webhook logs for a specific strategy."""
    logs = await db.webhook_logs_collection.find({"strategy_id": strategy_id, "user_id": user["_id"]}).sort("created_at", -1).to_list(100)
    for log in logs:
        log["_id"] = str(log["_id"])
    return logs
