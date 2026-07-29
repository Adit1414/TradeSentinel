"""Watchlist CRUD API router."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, WatchlistItem
from app.schemas import WatchlistItemCreate, WatchlistItemUpdate, WatchlistItemResponse
from app.services.data_fetcher import search_tickers
from app.utils.auth_utils import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/watchlist", tags=["Watchlist"])


@router.get("/", response_model=list[WatchlistItemResponse])
async def list_all_watchlist_items(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all watchlist items across all modes (scoped to current user)."""
    result = await db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.user_id == current_user.id)
        .order_by(WatchlistItem.mode, WatchlistItem.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{mode}", response_model=list[WatchlistItemResponse])
async def list_watchlist_by_mode(
    mode: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List watchlist items for a specific mode (intraday, short_selling, long_term)."""
    if mode not in ("intraday", "short_selling", "long_term"):
        raise HTTPException(status_code=400, detail="Invalid mode")

    result = await db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.user_id == current_user.id, WatchlistItem.mode == mode)
        .order_by(WatchlistItem.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=WatchlistItemResponse, status_code=201)
async def add_watchlist_item(
    item: WatchlistItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new stock to a watchlist mode."""
    ticker = item.ticker.strip().upper()

    # Check for duplicates in the same mode for this user
    existing = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == current_user.id,
            WatchlistItem.ticker == ticker,
            WatchlistItem.mode == item.mode,
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=409,
            detail=f"{ticker} already exists in {item.mode} watchlist",
        )

    # Try to get display name from yfinance if not provided
    display_name = item.display_name
    if not display_name:
        results = search_tickers(ticker, max_results=1)
        if results:
            display_name = results[0].get("name", ticker)
        else:
            display_name = ticker

    db_item = WatchlistItem(
        user_id=current_user.id,
        ticker=ticker,
        display_name=display_name,
        mode=item.mode,
        is_active=True,
    )
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)

    logger.info(f"Added {ticker} to {item.mode} watchlist (user={current_user.email})")
    return db_item


@router.put("/{item_id}", response_model=WatchlistItemResponse)
async def update_watchlist_item(
    item_id: int,
    update: WatchlistItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a watchlist item."""
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == current_user.id,
        )
    )
    db_item = result.scalars().first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)

    await db.commit()
    await db.refresh(db_item)
    return db_item


@router.delete("/{item_id}", status_code=204)
async def delete_watchlist_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a stock from a watchlist."""
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == current_user.id,
        )
    )
    db_item = result.scalars().first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    await db.delete(db_item)
    await db.commit()
    logger.info(f"Deleted {db_item.ticker} from {db_item.mode} watchlist (user={current_user.email})")
