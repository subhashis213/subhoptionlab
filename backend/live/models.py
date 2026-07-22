"""
Data models for the Live and Paper Trading module.
These models represent the structure of documents stored in MongoDB.
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class BrokerCredentials(BaseModel):
    """Stores encrypted broker API keys (e.g. Upstox)."""
    id: str = Field(..., alias="_id")
    user_id: str = "default_user"  # Single-tenant for now
    broker: Literal["upstox"] = "upstox"
    encrypted_access_token: str
    encrypted_api_key: Optional[str] = None
    connected_at: datetime
    is_active: bool = True


class LiveStrategy(BaseModel):
    """Represents a saved strategy deployed to the live/paper runner."""
    id: str = Field(..., alias="_id")
    user_id: str = "default_user"
    strategy_id: str  # FK to existing backtest strategies collection
    mode: Literal["paper"] = "paper"  # PAPER TRADE ONLY — live mode structurally removed
    status: Literal["active", "stopped", "killed"]
    max_daily_loss: float
    max_lots: int
    deployed_at: datetime
    stopped_at: Optional[datetime] = None


class BaseOrder(BaseModel):
    """Base schema for both paper and live orders."""
    id: str = Field(..., alias="_id")
    live_strategy_id: str
    leg_index: int
    action: Literal["BUY", "SELL"]
    symbol: str
    strike: float
    option_type: Literal["CE", "PE"]
    order_type: Literal["entry", "exit"]
    price: float
    qty: int
    timestamp: datetime
    exit_reason: Optional[str] = None  # e.g., "leg_sl_hit", "time_exit", "killed"


class PaperOrder(BaseOrder):
    """Simulated orders during paper trading."""
    broker_order_id: None = None


# NOTE: LiveOrder class has been REMOVED.
# PAPER TRADE ONLY — no live broker order model exists in this codebase.


class LivePosition(BaseModel):
    """Tracks open/closed legs for a deployed live strategy."""
    id: str = Field(..., alias="_id")
    live_strategy_id: str
    leg_index: int
    status: Literal["open", "closed"]
    entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    updated_at: datetime
