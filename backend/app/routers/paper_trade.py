"""Paper Trade Journal API router.

Endpoints:
  GET  /api/paper-trade/snapshot/{ticker}   — live indicator snapshot
  POST /api/paper-trade/open                — open a new paper trade
  POST /api/paper-trade/close/{id}          — close a trade and record PnL
  PUT  /api/paper-trade/{id}/notes          — save reflection notes
  GET  /api/paper-trade/                    — list all paper trades
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PaperTrade, User, _utcnow
from app.schemas import (
    ClosePaperTradeRequest,
    NotesUpdateRequest,
    OpenPaperTradeRequest,
    PaperTradeResponse,
    SnapshotResponse,
    VALID_DIRECTIONS,
)
from app.services.paper_trade_service import (
    calculate_break_even_and_sl,
    compute_close_pnl,
    fetch_snapshot,
)
from app.utils.auth_utils import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/paper-trade", tags=["Paper Trade"])


# ── Snapshot ───────────────────────────────────────────────────────────────────

@router.get("/snapshot/{ticker}", response_model=SnapshotResponse)
async def get_snapshot(
    ticker: str,
    mode: str = Query(
        "intraday",
        pattern=r"^(intraday|short_selling|long_term)$",
        description="Trading mode — determines data interval and indicators",
    ),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch the current price and all 4 indicator values for a given ticker.

    This is called by the frontend modal on open. Because yfinance can lag
    behind live broker feeds, all returned values are editable by the user
    before confirming the trade.
    """
    snapshot = fetch_snapshot(ticker, mode=mode)
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch market data or compute indicators for '{ticker}'. "
                   f"Ensure it is a valid NSE symbol.",
        )
    return snapshot


# ── Open Trade ─────────────────────────────────────────────────────────────────

@router.post("/open", response_model=PaperTradeResponse, status_code=201)
async def open_paper_trade(
    payload: OpenPaperTradeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Log a new paper trade entry.

    Accepts the final (possibly user-overridden) indicator values, calculates
    the exact NSE-fee-adjusted break-even price and suggested stop-loss, then
    persists the full snapshot to the database.
    """
    if payload.trade_direction not in VALID_DIRECTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"trade_direction must be one of: {', '.join(sorted(VALID_DIRECTIONS))}",
        )

    # Map direction → mode for the charge calculator
    be_data = calculate_break_even_and_sl(
        trade_direction=payload.trade_direction,
        entry_price=payload.entry_price,
        quantity=payload.quantity,
        vwap=payload.snapshot_vwap,
        supertrend=payload.snapshot_supertrend,
        ema_200=payload.snapshot_ema_200,
        weekly_sma_200=payload.snapshot_weekly_sma_200,
    )

    trade = PaperTrade(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        ticker=payload.ticker.upper().replace(".NS", ""),
        trade_direction=payload.trade_direction,
        quantity=payload.quantity,
        status="OPEN",
        entry_time=_utcnow(),
        entry_price=payload.entry_price,
        is_manual_override=payload.is_manual_override,
        # Indicator snapshot (intraday / short-sell fields)
        indicator_snapshot_rsi=payload.snapshot_rsi,
        indicator_snapshot_macd_fast=payload.snapshot_macd_fast,
        indicator_snapshot_macd_signal=payload.snapshot_macd_signal,
        indicator_snapshot_vwap=payload.snapshot_vwap,
        indicator_snapshot_supertrend=payload.snapshot_supertrend,
        # Weekly long-term indicator snapshot (None for non-LONG_TERM trades)
        indicator_snapshot_weekly_sma_200=payload.snapshot_weekly_sma_200,
        indicator_snapshot_weekly_rsi=payload.snapshot_weekly_rsi,
        indicator_snapshot_weekly_macd=payload.snapshot_weekly_macd,
        indicator_snapshot_weekly_bb_lower=payload.snapshot_weekly_bb_lower,
        # Calculated targets
        calculated_break_even_price=be_data["break_even_price"],
        suggested_stop_loss_price=be_data["suggested_stop_loss_price"],
    )

    db.add(trade)
    await db.commit()
    await db.refresh(trade)

    logger.info(
        f"Paper trade opened: {trade.ticker} {trade.trade_direction} "
        f"×{trade.quantity} @ ₹{trade.entry_price} | "
        f"BE=₹{trade.calculated_break_even_price} SL=₹{trade.suggested_stop_loss_price} "
        f"user={current_user.email}"
    )
    return trade


# ── Close Trade ────────────────────────────────────────────────────────────────

@router.post("/close/{trade_id}", response_model=PaperTradeResponse)
async def close_paper_trade(
    trade_id: str,
    payload: ClosePaperTradeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Close an open paper trade and record the exit price + net PnL.

    Calculates both gross PnL and exact net PnL after all NSE statutory fees.
    """
    result = await db.execute(
        select(PaperTrade).where(
            PaperTrade.id == trade_id,
            PaperTrade.user_id == current_user.id,
        )
    )
    trade = result.scalar_one_or_none()
    if trade is None:
        raise HTTPException(status_code=404, detail=f"Paper trade '{trade_id}' not found.")
    if trade.status == "CLOSED":
        raise HTTPException(
            status_code=409, detail=f"Paper trade '{trade_id}' is already closed."
        )

    pnl = compute_close_pnl(
        trade_direction=trade.trade_direction,
        entry_price=trade.entry_price,
        exit_price=payload.exit_price,
        quantity=trade.quantity,
    )

    trade.exit_price = payload.exit_price
    trade.exit_time = _utcnow()
    trade.status = "CLOSED"
    trade.pnl_gross = pnl["pnl_gross"]
    trade.pnl_net_after_fees = pnl["pnl_net_after_fees"]

    await db.commit()
    await db.refresh(trade)

    logger.info(
        f"Paper trade closed: {trade.ticker} {trade.trade_direction} "
        f"exit=₹{trade.exit_price} | gross=₹{trade.pnl_gross} net=₹{trade.pnl_net_after_fees}"
    )
    return trade


# ── Update Notes ───────────────────────────────────────────────────────────────

@router.put("/{trade_id}/notes", response_model=PaperTradeResponse)
async def update_notes(
    trade_id: str,
    payload: NotesUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save or update the qualitative reflection notes on a paper trade."""
    result = await db.execute(
        select(PaperTrade).where(
            PaperTrade.id == trade_id,
            PaperTrade.user_id == current_user.id,
        )
    )
    trade = result.scalar_one_or_none()
    if trade is None:
        raise HTTPException(status_code=404, detail=f"Paper trade '{trade_id}' not found.")

    trade.reflection_notes = payload.reflection_notes
    await db.commit()
    await db.refresh(trade)
    return trade


# ── List Trades ────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[PaperTradeResponse])
async def list_paper_trades(
    status: str | None = Query(
        None,
        pattern=r"^(OPEN|CLOSED)$",
        description="Filter by trade status",
    ),
    ticker: str | None = Query(None, description="Filter by ticker symbol"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return all paper trades for the current user, optionally filtered by status and/or ticker.

    Results are ordered newest-first.
    """
    stmt = select(PaperTrade).where(PaperTrade.user_id == current_user.id)
    if status:
        stmt = stmt.where(PaperTrade.status == status)
    if ticker:
        stmt = stmt.where(PaperTrade.ticker == ticker.upper().replace(".NS", ""))

    stmt = stmt.order_by(PaperTrade.entry_time.desc())
    result = await db.execute(stmt)
    return result.scalars().all()
