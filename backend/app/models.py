"""SQLAlchemy ORM models for TradingHelper."""

import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """A user authenticated via Google OAuth."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    google_sub: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_login_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class WatchlistItem(Base):
    """A stock ticker tracked in one of the three watchlist modes."""

    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=True)
    mode: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "intraday" | "short_selling" | "long_term"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )


class Position(Base):
    """A manually-entered trade position for tracking and break-even calculation."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "intraday" | "short_selling" | "long_term"
    direction: Mapped[str] = mapped_column(
        String(4), nullable=False
    )  # "BUY" | "SELL"
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    target_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AlertHistory(Base):
    """A log entry for when a confluence alert was triggered."""

    __tablename__ = "alert_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    indicator_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    price_at_alert: Mapped[float] = mapped_column(Float, nullable=False)
    notified_via: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class AppSettings(Base):
    """Key-value store for application configuration."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class PaperTrade(Base):
    """A paper trade entry logged by the user for educational journaling.

    Captures an exact indicator snapshot at entry time, calculates
    NSE-accurate break-even and stop-loss, and tracks PnL on close.
    trade_direction values: INTRADAY_BUY | SHORT_SELL | LONG_TERM
    """

    __tablename__ = "paper_trades"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    trade_direction: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # INTRADAY_BUY | SHORT_SELL | LONG_TERM
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="OPEN")  # OPEN | CLOSED

    # Timing
    entry_time: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Prices
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Override flag — True if user manually corrected any auto-fetched value
    is_manual_override: Mapped[bool] = mapped_column(Boolean, default=False)

    # Indicator snapshot at entry
    indicator_snapshot_rsi: Mapped[float] = mapped_column(Float, nullable=False)
    indicator_snapshot_macd_fast: Mapped[float] = mapped_column(Float, nullable=False)
    indicator_snapshot_macd_signal: Mapped[float] = mapped_column(Float, nullable=False)
    indicator_snapshot_vwap: Mapped[float | None] = mapped_column(Float, nullable=True)
    indicator_snapshot_supertrend: Mapped[float] = mapped_column(Float, nullable=False)

    # Calculated targets
    calculated_break_even_price: Mapped[float] = mapped_column(Float, nullable=False)
    suggested_stop_loss_price: Mapped[float] = mapped_column(Float, nullable=False)

    # PnL (populated on close)
    pnl_gross: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_net_after_fees: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Journal reflection
    reflection_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional hard stop-loss set manually by the user (overrides suggested_stop_loss_price)
    user_defined_stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Exit alert cooldown flags ─────────────────────────────────────────────
    # Each flag is set True the moment that specific exit condition fires a
    # notification. It is reset to False by the exit scanner when the condition
    # is no longer true, enabling re-notification on a fresh trigger.
    exit_alert_vwap_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    exit_alert_supertrend_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    exit_alert_stoploss_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    exit_alert_rsi_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    exit_alert_macd_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    # Break-even is a one-shot lifetime event; flag is never reset.
    exit_alert_breakeven_sent: Mapped[bool] = mapped_column(Boolean, default=False)

