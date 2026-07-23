"""
Pydantic models for the Paper Trading platform.
Covers: Users, Wallets, Chip Transactions, Strategies, Strategy Legs, Trade History.

PAPER TRADE ONLY — no model for live broker orders exists.
"""

from datetime import datetime
from typing import Optional, Literal, List, Union
from pydantic import BaseModel, Field, EmailStr
import uuid


def _gen_id() -> str:
    return str(uuid.uuid4())


# ── Users ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    """Registration request."""
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=200)
    phone: str = Field("", max_length=15)
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    """Login request."""
    email: str
    password: str


class UserInDB(BaseModel):
    """User document stored in MongoDB."""
    id: str = Field(default_factory=_gen_id, alias="_id")
    name: str
    email: str
    phone: str = ""
    password_hash: str
    role: Literal["admin", "user"] = "user"
    status: Literal["active", "blocked"] = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}


class UserResponse(BaseModel):
    """User info returned to clients (no password)."""
    id: str = Field(alias="_id")
    name: str
    email: str
    phone: str = ""
    role: str
    status: str
    created_at: datetime

    model_config = {"populate_by_name": True}


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ── Wallets ────────────────────────────────────────────────────────────────────

class WalletInDB(BaseModel):
    """Wallet document — one per user, admin-managed."""
    user_id: str
    virtual_chips_balance: float = 0.0
    total_added: float = 0.0
    total_removed: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class WalletResponse(BaseModel):
    """Wallet info returned to clients."""
    user_id: str
    virtual_chips_balance: float
    total_added: float
    total_removed: float
    unrealized_pnl: float = 0.0
    net_worth: float = 0.0
    used_margin: float = 0.0
    available_margin: float = 0.0
    last_updated: Optional[datetime] = None


# ── Chip Transactions ──────────────────────────────────────────────────────────

class ChipTransactionCreate(BaseModel):
    """Request to add/remove chips (admin action)."""
    amount: float = Field(..., gt=0)
    reason: str = Field(..., min_length=1, max_length=500)


class ChipTransactionInDB(BaseModel):
    """Chip transaction document — audit trail."""
    id: str = Field(default_factory=_gen_id, alias="_id")
    user_id: str
    admin_id: str
    type: Literal["add", "remove"]
    amount: float
    reason: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}


# ── Strategies ─────────────────────────────────────────────────────────────────

class LegCreate(BaseModel):
    """Leg definition when creating a strategy."""
    symbol: str  # e.g., "NIFTY", "BANKNIFTY"
    expiry: str  # e.g., "2026-07-24"
    strike: Union[float, str]
    option_type: Literal["CE", "PE"]
    side: Literal["BUY", "SELL"]
    qty: int = Field(..., ge=1, description="Number of lots")
    order_type: Literal["MARKET", "LIMIT"] = "MARKET"
    limit_price: float = Field(0.0, ge=0)
    sl_type: Literal["points", "percentage"] = "points"
    sl_value: float = Field(0.0, ge=0)
    target_type: Literal["points", "percentage"] = "points"
    target_value: float = Field(0.0, ge=0)
    instrument_key: Optional[str] = None


class StrategyCreate(BaseModel):
    """Request to create a new paper trading strategy."""
    name: str = Field(..., min_length=1, max_length=200)
    underlying: Literal["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCAPNIFTY"]
    move_sl_to_cost: bool = False
    entry_time: Optional[str] = None  # HH:MM format
    exit_time: Optional[str] = None   # HH:MM format
    legs: List[LegCreate] = Field(..., min_length=1)


class StrategyLegInDB(BaseModel):
    """Strategy leg document stored in MongoDB."""
    id: str = Field(default_factory=_gen_id, alias="_id")
    strategy_id: str
    symbol: str
    expiry: str
    strike: Union[float, str]
    option_type: Literal["CE", "PE"]
    side: Literal["BUY", "SELL"]
    qty: int  # in lots
    order_type: Literal["MARKET", "LIMIT"] = "MARKET"
    limit_price: float = 0.0
    entry_price: float = 0.0
    sl_type: Literal["points", "percentage"] = "points"
    sl_value: float = 0.0
    target_type: Literal["points", "percentage"] = "points"
    target_value: float = 0.0
    current_sl_price: Optional[float] = None
    current_target_price: Optional[float] = None
    current_status: Literal["pending_entry", "open", "sl_hit", "target_hit", "manually_closed"] = "open"
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    instrument_key: Optional[str] = None  # Upstox instrument key for quote fetching
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}


class StrategyInDB(BaseModel):
    """Strategy document stored in MongoDB."""
    id: str = Field(default_factory=_gen_id, alias="_id")
    user_id: str
    name: str
    underlying: Literal["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCAPNIFTY"]
    move_sl_to_cost: bool = False
    status: Literal["pending", "draft", "active", "closed"] = "draft"
    entry_time: Optional[str] = None
    exit_time: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}


class StrategyResponse(BaseModel):
    """Strategy with legs returned to clients."""
    id: str = Field(alias="_id")
    user_id: str
    name: str
    underlying: str
    move_sl_to_cost: bool
    status: str
    entry_time: Optional[str] = None
    exit_time: Optional[str] = None
    created_at: datetime
    closed_at: Optional[datetime] = None
    legs: List[dict] = []
    total_unrealized_pnl: float = 0.0

    model_config = {"populate_by_name": True}


# ── Trade History ──────────────────────────────────────────────────────────────

class TradeHistoryInDB(BaseModel):
    """Immutable trade log entry."""
    id: str = Field(default_factory=_gen_id, alias="_id")
    strategy_id: str
    leg_id: str
    user_id: str
    action: Literal["BUY", "SELL"]
    symbol: str
    strike: Union[float, str]
    option_type: Literal["CE", "PE"]
    price: float
    qty: int
    pnl: float = 0.0
    exit_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}


# ── Admin Overview ─────────────────────────────────────────────────────────────

class AdminOverview(BaseModel):
    """Global platform stats for admin dashboard."""
    total_users: int = 0
    active_users: int = 0
    blocked_users: int = 0
    total_capital_distributed: float = 0.0
    total_capital_in_play: float = 0.0
    active_strategies_count: int = 0


class UserStatusUpdate(BaseModel):
    """Request to update user status."""
    status: Literal["active", "blocked"]
