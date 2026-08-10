"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from pydantic import BaseModel, Field


# ── Watchlist ──────────────────────────────────────────────────────────────────

class WatchlistItemCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20, examples=["RELIANCE"])
    display_name: str | None = Field(None, max_length=100)
    mode: str = Field(..., pattern=r"^(intraday|short_selling|long_term)$")


class WatchlistItemUpdate(BaseModel):
    ticker: str | None = Field(None, max_length=20)
    display_name: str | None = Field(None, max_length=100)
    mode: str | None = Field(None, pattern=r"^(intraday|short_selling|long_term)$")
    is_active: bool | None = None


class WatchlistItemResponse(BaseModel):
    id: int
    ticker: str
    display_name: str | None
    mode: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Positions ──────────────────────────────────────────────────────────────────

class PositionCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)
    trade_type: str = Field(..., pattern=r"^(intraday|short_selling|long_term)$")
    direction: str = Field(..., pattern=r"^(BUY|SELL)$")
    quantity: int = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    target_profit: float | None = Field(None, ge=0)
    notes: str | None = None


class PositionUpdate(BaseModel):
    status: str | None = Field(None, pattern=r"^(OPEN|CLOSED)$")
    target_profit: float | None = None
    notes: str | None = None


class PositionResponse(BaseModel):
    id: int
    ticker: str
    trade_type: str
    direction: str
    quantity: int
    entry_price: float
    target_profit: float | None
    exit_price: float | None
    notes: str | None
    status: str
    created_at: datetime
    closed_at: datetime | None

    model_config = {"from_attributes": True}


class BreakEvenRequest(BaseModel):
    """Request schema for the break-even / target-price calculator."""
    trade_type: str = Field(..., pattern=r"^(intraday|short_selling|long_term)$")
    direction: str = Field(..., pattern=r"^(BUY|SELL)$")
    quantity: int = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    target_profit: float | None = Field(None, ge=0, description="Target profit in ₹")


class BreakEvenResponse(BaseModel):
    entry_price: float
    quantity: int
    trade_type: str
    direction: str
    buy_value: float
    sell_value_breakeven: float
    breakeven_price: float
    target_price: float | None = None
    total_charges_buy: float
    total_charges_sell: float
    charges_breakdown_buy: dict
    charges_breakdown_sell: dict
    net_profit: float


# ── Alerts ─────────────────────────────────────────────────────────────────────

class AlertResponse(BaseModel):
    id: int
    ticker: str
    mode: str
    alert_type: str
    indicator_data: dict | None
    price_at_alert: float
    notified_via: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertSettingsUpdate(BaseModel):
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    ntfy_topic: str | None = None
    scan_interval_intraday_seconds: int | None = Field(None, ge=30)
    scan_interval_longterm_seconds: int | None = Field(None, ge=60)


class NtfyTestRequest(BaseModel):
    topic: str | None = None


class TestNtfyRequest(BaseModel):
    topic: str | None = None


class TestTelegramRequest(BaseModel):
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None


# ── Market Data ────────────────────────────────────────────────────────────────

class ChartDataRequest(BaseModel):
    ticker: str
    interval: str = Field("5m", pattern=r"^(1m|5m|15m|1h|1d|1wk)$")
    period: str = Field("5d", pattern=r"^(\d+[dwm]|max)$")


class IndicatorStatus(BaseModel):
    """Current indicator values and their bull/bear status for a single ticker."""
    ticker: str
    mode: str
    price: float
    vwap: float | None = None
    ema_200: float | None = None
    supertrend_value: float
    supertrend_direction: int  # 1 = bullish, -1 = bearish
    rsi: float
    rsi_rising: bool
    macd_line: float
    macd_signal: float
    macd_histogram: float
    macd_crossover: str  # "bullish" | "bearish" | "none"
    confluence: bool
    timestamp: datetime


# ── Paper Trades ───────────────────────────────────────────────────────────────

VALID_DIRECTIONS = {"INTRADAY_BUY", "SHORT_SELL", "LONG_TERM"}


class SnapshotResponse(BaseModel):
    """Live market snapshot returned by GET /api/paper-trade/snapshot/{ticker}."""
    ticker: str
    mode: str
    price: float
    rsi: float
    macd_fast: float
    macd_signal: float
    vwap: float | None = None
    supertrend: float
    ema_200: float | None = None
    timestamp: datetime
    # Weekly indicators (populated only when mode="long_term")
    weekly_sma_200: float | None = None
    weekly_rsi: float | None = None
    weekly_macd_line: float | None = None
    weekly_macd_signal: float | None = None
    weekly_bb_lower: float | None = None


class OpenPaperTradeRequest(BaseModel):
    """Request body for POST /api/paper-trade/open."""
    ticker: str = Field(..., min_length=1, max_length=20)
    trade_direction: str = Field(
        ..., description="INTRADAY_BUY | SHORT_SELL | LONG_TERM"
    )
    quantity: int = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    # Indicator values (may be auto-fetched or manually overridden)
    snapshot_rsi: float
    snapshot_macd_fast: float
    snapshot_macd_signal: float
    snapshot_vwap: float | None = None
    snapshot_supertrend: float
    snapshot_ema_200: float | None = None
    is_manual_override: bool = False
    # Weekly long-term indicator snapshot (only for LONG_TERM direction)
    snapshot_weekly_sma_200: float | None = None
    snapshot_weekly_rsi: float | None = None
    snapshot_weekly_macd: float | None = None
    snapshot_weekly_bb_lower: float | None = None


class ClosePaperTradeRequest(BaseModel):
    """Request body for POST /api/paper-trade/close/{id}."""
    exit_price: float = Field(..., gt=0)


class NotesUpdateRequest(BaseModel):
    """Request body for PUT /api/paper-trade/{id}/notes."""
    reflection_notes: str


class PaperTradeResponse(BaseModel):
    """Full paper trade record returned from all paper trade endpoints."""
    id: str
    ticker: str
    trade_direction: str
    quantity: int
    status: str
    entry_time: datetime
    exit_time: datetime | None = None
    entry_price: float
    exit_price: float | None = None
    is_manual_override: bool
    indicator_snapshot_rsi: float
    indicator_snapshot_macd_fast: float
    indicator_snapshot_macd_signal: float
    indicator_snapshot_vwap: float | None = None
    indicator_snapshot_supertrend: float
    indicator_snapshot_ema_200: float | None = None
    # Weekly long-term indicator snapshots (None for intraday / short-sell trades)
    indicator_snapshot_weekly_sma_200: float | None = None
    indicator_snapshot_weekly_rsi: float | None = None
    indicator_snapshot_weekly_macd: float | None = None
    indicator_snapshot_weekly_bb_lower: float | None = None
    calculated_break_even_price: float
    suggested_stop_loss_price: float
    pnl_gross: float | None = None
    pnl_net_after_fees: float | None = None
    reflection_notes: str | None = None
    # User-overridable hard stop-loss
    user_defined_stop_loss: float | None = None
    # Exit alert cooldown flags (read-only — managed by background scanner)
    exit_alert_vwap_sent: bool = False
    exit_alert_supertrend_sent: bool = False
    exit_alert_stoploss_sent: bool = False
    exit_alert_rsi_sent: bool = False
    exit_alert_macd_sent: bool = False
    exit_alert_breakeven_sent: bool = False

    model_config = {"from_attributes": True}


