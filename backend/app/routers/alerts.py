"""Alert history and notification settings API router."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AlertHistory, AppSettings, User
from app.schemas import AlertResponse, AlertSettingsUpdate, TestNtfyRequest, TestTelegramRequest
from app.services.notifier import test_telegram_connection, test_ntfy_connection
from app.utils.auth_utils import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("/", response_model=list[AlertResponse])
async def list_alerts(
    mode: str | None = None,
    ticker: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get alert history for the current user with optional filters."""
    query = (
        select(AlertHistory)
        .where(AlertHistory.user_id == current_user.id)
        .order_by(AlertHistory.created_at.desc())
    )

    if mode:
        query = query.where(AlertHistory.mode == mode)
    if ticker:
        query = query.where(AlertHistory.ticker == ticker.upper())

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/count")
async def get_alert_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get total alert count for the current user."""
    result = await db.execute(
        select(func.count(AlertHistory.id)).where(AlertHistory.user_id == current_user.id)
    )
    count = result.scalar()
    return {"count": count}


@router.get("/settings")
async def get_alert_settings(db: AsyncSession = Depends(get_db)):
    """Get current notification settings."""
    result = await db.execute(select(AppSettings))
    settings_rows = result.scalars().all()

    settings = {}
    for row in settings_rows:
        settings[row.key] = row.value

    return {
        "telegram_bot_token": settings.get("telegram_bot_token", ""),
        "telegram_chat_id": settings.get("telegram_chat_id", ""),
        "ntfy_topic": settings.get("ntfy_topic", ""),
        "telegram_configured": bool(
            settings.get("telegram_bot_token") and settings.get("telegram_chat_id")
        ),
        "ntfy_configured": bool(settings.get("ntfy_topic")),
    }


@router.put("/settings")
async def update_alert_settings(
    update: AlertSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update notification settings."""
    update_data = update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if value is not None:
            result = await db.execute(
                select(AppSettings).where(AppSettings.key == key)
            )
            existing = result.scalars().first()
            if existing:
                existing.value = str(value)
            else:
                db.add(AppSettings(key=key, value=str(value)))

    await db.commit()
    return {"status": "updated", "keys": list(update_data.keys())}


@router.post("/test-telegram")
async def test_telegram(
    request: TestTelegramRequest | None = None,
    db: AsyncSession = Depends(get_db)
):
    """Send a test notification via Telegram."""
    result = await db.execute(select(AppSettings))
    settings_rows = result.scalars().all()
    settings = {row.key: row.value for row in settings_rows}

    token = request.telegram_bot_token if request and request.telegram_bot_token else settings.get("telegram_bot_token")
    chat_id = request.telegram_chat_id if request and request.telegram_chat_id else settings.get("telegram_chat_id")

    if not token or not chat_id:
        raise HTTPException(
            status_code=400,
            detail="Telegram not configured. Set bot_token and chat_id first.",
        )

    res = await test_telegram_connection(bot_token=token, chat_id=chat_id)
    if not res["success"]:
        raise HTTPException(status_code=502, detail=res.get("error", "Unknown error"))

    return res


@router.post("/test-ntfy")
async def test_ntfy(
    request: TestNtfyRequest | None = None,
    db: AsyncSession = Depends(get_db)
):
    """Send a test push notification via Ntfy.sh."""
    result = await db.execute(select(AppSettings))
    settings_rows = result.scalars().all()
    settings = {row.key: row.value for row in settings_rows}

    topic = request.topic if request and request.topic else settings.get("ntfy_topic")

    if not topic:
        raise HTTPException(
            status_code=400,
            detail="Ntfy topic not configured. Enter your topic name first.",
        )

    res = await test_ntfy_connection(topic=topic)
    if not res["success"]:
        raise HTTPException(status_code=502, detail=res.get("error", "Unknown error"))

    return res
