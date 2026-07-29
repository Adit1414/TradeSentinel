"""Position tracker and break-even calculator API router."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Position, User
from app.schemas import (
    PositionCreate,
    PositionUpdate,
    PositionResponse,
    BreakEvenRequest,
    BreakEvenResponse,
)
from app.services.calculator import calculate_breakeven
from app.utils.auth_utils import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/positions", tags=["Positions"])


@router.get("/", response_model=list[PositionResponse])
async def list_positions(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all positions for the current user, optionally filtered by status (OPEN/CLOSED)."""
    query = (
        select(Position)
        .where(Position.user_id == current_user.id)
        .order_by(Position.created_at.desc())
    )
    if status:
        query = query.where(Position.status == status.upper())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=PositionResponse, status_code=201)
async def create_position(
    position: PositionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new manual position entry and calculate its break-even price."""
    # Calculate break-even on creation
    calc_result = calculate_breakeven(
        trade_type=position.trade_type,
        direction=position.direction,
        quantity=position.quantity,
        entry_price=position.entry_price,
        target_profit=position.target_profit,
    )

    db_position = Position(
        user_id=current_user.id,
        ticker=position.ticker.strip().upper(),
        trade_type=position.trade_type,
        direction=position.direction,
        quantity=position.quantity,
        entry_price=position.entry_price,
        target_profit=position.target_profit,
        exit_price=calc_result["breakeven_price"],
        notes=position.notes,
        status="OPEN",
    )

    db.add(db_position)
    await db.commit()
    await db.refresh(db_position)

    logger.info(
        f"Position created: {db_position.direction} {db_position.quantity}x "
        f"{db_position.ticker} @ ₹{db_position.entry_price} "
        f"(breakeven: ₹{db_position.exit_price}) user={current_user.email}"
    )
    return db_position


@router.put("/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: int,
    update: PositionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update position status, notes, or target profit."""
    result = await db.execute(
        select(Position).where(
            Position.id == position_id,
            Position.user_id == current_user.id,
        )
    )
    db_pos = result.scalars().first()
    if not db_pos:
        raise HTTPException(status_code=404, detail="Position not found")

    update_data = update.model_dump(exclude_unset=True)

    # If target_profit changes, recalculate exit price
    if "target_profit" in update_data:
        calc_result = calculate_breakeven(
            trade_type=db_pos.trade_type,
            direction=db_pos.direction,
            quantity=db_pos.quantity,
            entry_price=db_pos.entry_price,
            target_profit=update_data["target_profit"],
        )
        db_pos.exit_price = calc_result.get("target_price") or calc_result["breakeven_price"]

    # If closing the position, set closed_at
    if update_data.get("status") == "CLOSED":
        db_pos.closed_at = datetime.now(timezone.utc)

    for key, value in update_data.items():
        setattr(db_pos, key, value)

    await db.commit()
    await db.refresh(db_pos)
    return db_pos


@router.delete("/{position_id}", status_code=204)
async def delete_position(
    position_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a position entry."""
    result = await db.execute(
        select(Position).where(
            Position.id == position_id,
            Position.user_id == current_user.id,
        )
    )
    db_pos = result.scalars().first()
    if not db_pos:
        raise HTTPException(status_code=404, detail="Position not found")

    await db.delete(db_pos)
    await db.commit()


@router.post("/calculate", response_model=BreakEvenResponse)
async def calculate_break_even(
    req: BreakEvenRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Calculate break-even and target exit prices for given trade parameters.

    This is a stateless calculation endpoint — no position is saved.
    """
    result = calculate_breakeven(
        trade_type=req.trade_type,
        direction=req.direction,
        quantity=req.quantity,
        entry_price=req.entry_price,
        target_profit=req.target_profit,
    )
    return result
