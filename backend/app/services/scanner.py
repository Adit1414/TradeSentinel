"""Background scanner using APScheduler.

Periodically scans watchlist stocks, calculates indicators,
checks for confluence, and dispatches alerts.
"""

import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import get_settings
from app.database import _get_session_maker
from app.models import WatchlistItem, AlertHistory, AppSettings
from app.services.data_fetcher import fetch_ohlcv
from app.services.indicators import calculate_indicators
from app.services.confluence import check_confluence
from app.services.notifier import send_telegram_alert, send_ntfy_alert
from app.services.exit_scanner import scan_open_trades_for_exits

logger = logging.getLogger(__name__)

# Track last alert time per (ticker, mode) to enforce cooldowns
_alert_cooldowns: dict[tuple[str, str], datetime] = {}

# Global scheduler reference
scheduler: AsyncIOScheduler | None = None


def _is_market_hours() -> bool:
    """Check if current time is within NSE market hours (9:15 AM – 3:30 PM IST)."""
    settings = get_settings()
    # IST = UTC+5:30
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)

    # Skip weekends (Saturday=5, Sunday=6)
    if now.weekday() >= 5:
        return False

    market_open = now.replace(
        hour=settings.market_open_hour,
        minute=settings.market_open_minute,
        second=0,
        microsecond=0,
    )
    market_close = now.replace(
        hour=settings.market_close_hour,
        minute=settings.market_close_minute,
        second=0,
        microsecond=0,
    )

    return market_open <= now <= market_close


def _is_in_cooldown(ticker: str, mode: str) -> bool:
    """Check if we're in cooldown period for this ticker+mode."""
    settings = get_settings()
    key = (ticker, mode)

    if key not in _alert_cooldowns:
        return False

    last_alert = _alert_cooldowns[key]
    now = datetime.now(timezone.utc)

    if mode in ("intraday", "short_selling"):
        cooldown = timedelta(minutes=settings.alert_cooldown_intraday_minutes)
    else:
        cooldown = timedelta(hours=settings.alert_cooldown_longterm_hours)

    return (now - last_alert) < cooldown


async def _scan_mode(mode: str, interval: str, period: str):
    """
    Scan all active watchlist items for a specific mode.

    Args:
        mode: "intraday", "short_selling", or "long_term".
        interval: yfinance interval ("5m" or "1d").
        period: yfinance period ("5d" or "1y").
    """
    if not _is_market_hours() and mode != "long_term":
        logger.debug(f"Outside market hours, skipping {mode} scan")
        return

    logger.info(f"Starting {mode} scan (interval={interval}, period={period})")

    try:
        async with _get_session_maker()() as session:
            result = await session.execute(
                select(WatchlistItem).where(
                    WatchlistItem.mode == mode,
                    WatchlistItem.is_active == True,
                )
            )
            items = result.scalars().all()

        if not items:
            logger.debug(f"No active watchlist items for {mode}")
            return

        for item in items:
            try:
                await _check_single_stock(item, mode, interval, period)
            except Exception as e:
                logger.error(f"Error scanning {item.ticker} ({mode}): {e}")
                continue

    except Exception as e:
        logger.error(f"Error in {mode} scan: {e}", exc_info=True)


async def _check_single_stock(
    item: WatchlistItem,
    mode: str,
    interval: str,
    period: str,
):
    """Fetch data, calculate indicators, check confluence for a single stock."""

    # Check cooldown first
    if _is_in_cooldown(item.ticker, mode):
        logger.debug(f"Skipping {item.ticker} ({mode}) — in cooldown")
        return

    # Fetch OHLCV data
    df = fetch_ohlcv(item.ticker, interval=interval, period=period)
    if df.empty:
        logger.warning(f"No data for {item.ticker}")
        return

    # Calculate indicators
    indicators = calculate_indicators(df, mode=mode)
    if indicators is None:
        logger.warning(f"Insufficient data for indicators: {item.ticker}")
        return

    # Check confluence
    result = check_confluence(indicators, mode)

    if result.is_aligned:
        logger.info(
            f"🎯 CONFLUENCE for {item.ticker} ({mode}) at ₹{indicators.price:.2f}"
        )

        # Set cooldown
        _alert_cooldowns[(item.ticker, mode)] = datetime.now(timezone.utc)

        # Determine alert type
        alert_type = (
            "confluence_bearish" if mode == "short_selling" else "confluence_bullish"
        )

        # Fetch settings from DB to get custom bot tokens/topics if updated in UI
        ntfy_topic = None
        tg_token = None
        tg_chat = None

        try:
            async with _get_session_maker()() as session:
                st_res = await session.execute(select(AppSettings))
                st_map = {r.key: r.value for r in st_res.scalars().all()}
                ntfy_topic = st_map.get("ntfy_topic")
                tg_token = st_map.get("telegram_bot_token")
                tg_chat = st_map.get("telegram_chat_id")
        except Exception:
            pass

        # Send Telegram notification if configured
        tg_sent = await send_telegram_alert(
            ticker=item.ticker,
            mode=mode,
            price=indicators.price,
            details=result.details,
            bot_token=tg_token,
            chat_id=tg_chat,
        )

        # Send Ntfy push notification if configured
        ntfy_sent = await send_ntfy_alert(
            ticker=item.ticker,
            mode=mode,
            price=indicators.price,
            details=result.details,
            topic=ntfy_topic,
        )

        notified_methods = []
        if tg_sent:
            notified_methods.append("telegram")
        if ntfy_sent:
            notified_methods.append("ntfy")

        notified_via = ",".join(notified_methods) if notified_methods else "none"

        # Log to database
        try:
            async with _get_session_maker()() as session:
                alert = AlertHistory(
                    ticker=item.ticker,
                    mode=mode,
                    alert_type=alert_type,
                    indicator_data={
                        "price": indicators.price,
                        "vwap": indicators.vwap,
                        "ema_200": indicators.ema_200,
                        "supertrend": indicators.supertrend_value,
                        "supertrend_dir": indicators.supertrend_direction,
                        "rsi": indicators.rsi,
                        "macd": indicators.macd_line,
                        "macd_signal": indicators.macd_signal,
                        "checks": result.checks,
                    },
                    price_at_alert=indicators.price,
                    notified_via=notified_via,
                )
                session.add(alert)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to log alert: {e}")


async def scan_intraday():
    """Scan intraday watchlist stocks (5-minute timeframe)."""
    await _scan_mode("intraday", interval="5m", period="5d")


async def scan_short_selling():
    """Scan short selling watchlist stocks (5-minute timeframe)."""
    await _scan_mode("short_selling", interval="5m", period="5d")


async def scan_long_term():
    """Scan long-term watchlist stocks (daily timeframe)."""
    await _scan_mode("long_term", interval="1d", period="1y")


async def scan_exit_alerts():
    """Scan all open paper trades for exit conditions (Stop-Loss & Take-Profit).

    Runs only during NSE market hours so indicators are fresh intraday data.
    For LONG_TERM trades this uses daily candles; intraday uses 5-min candles.
    Exits early with no DB queries if there are no open paper trades.
    """
    if not _is_market_hours():
        logger.debug("Outside market hours, skipping exit alert scan")
        return
    await scan_open_trades_for_exits()


async def purge_old_alerts():
    """Delete AlertHistory rows older than 2 trading days (weekdays).

    Runs once daily at 15:35 IST (just after market close).
    Only AlertHistory is ever deleted — PaperTrade rows are never touched.

    Algorithm:
        Start from today in IST and walk backwards, counting only weekdays
        (Mon–Fri) until we have counted 2 full trading days.  Any alert
        created *before* that cutoff date (at midnight IST) is deleted.
    """
    from sqlalchemy import delete as sa_delete

    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(ist).date()

    # Walk backwards counting weekdays
    counted = 0
    cursor = today
    while counted < 2:
        cursor -= timedelta(days=1)
        if cursor.weekday() < 5:  # 0=Mon … 4=Fri
            counted += 1

    # cutoff = midnight IST at the start of that day, converted to UTC
    cutoff_ist = datetime(
        cursor.year, cursor.month, cursor.day,
        0, 0, 0, tzinfo=ist
    )
    cutoff_utc = cutoff_ist.astimezone(timezone.utc).replace(tzinfo=None)

    try:
        async with _get_session_maker()() as session:
            result = await session.execute(
                sa_delete(AlertHistory).where(
                    AlertHistory.created_at < cutoff_utc
                )
            )
            deleted = result.rowcount
            await session.commit()

        if deleted:
            logger.info(
                f"🗑️  Purged {deleted} alert(s) older than "
                f"{cursor.isoformat()} (2 trading days back)"
            )
        else:
            logger.debug("Alert purge: nothing to delete")
    except Exception as e:
        logger.error(f"Alert purge failed: {e}", exc_info=True)


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler with all scan jobs."""
    global scheduler
    settings = get_settings()

    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

    # Intraday scan — every N seconds during market hours
    scheduler.add_job(
        scan_intraday,
        "interval",
        seconds=settings.scan_interval_intraday_seconds,
        id="scan_intraday",
        name="Intraday Scanner",
        replace_existing=True,
    )

    # Short selling scan — same interval as intraday
    scheduler.add_job(
        scan_short_selling,
        "interval",
        seconds=settings.scan_interval_intraday_seconds,
        id="scan_short_selling",
        name="Short Selling Scanner",
        replace_existing=True,
    )

    # Long-term scan — every N seconds (less frequent)
    scheduler.add_job(
        scan_long_term,
        "interval",
        seconds=settings.scan_interval_longterm_seconds,
        id="scan_long_term",
        name="Long-Term Scanner",
        replace_existing=True,
    )

    # Exit alert scan — same cadence as intraday, only for open paper trades
    scheduler.add_job(
        scan_exit_alerts,
        "interval",
        seconds=settings.scan_interval_intraday_seconds,
        id="scan_exit_alerts",
        name="Exit Alert Scanner",
        replace_existing=True,
    )

    # Daily alert purge — runs at 15:35 IST (5 min after market close)
    # Deletes AlertHistory rows older than 2 trading days.
    # PaperTrade rows are NEVER touched by this job.
    scheduler.add_job(
        purge_old_alerts,
        "cron",
        hour=15,
        minute=35,
        timezone="Asia/Kolkata",
        id="purge_old_alerts",
        name="Alert History Purge (2 trading days)",
        replace_existing=True,
    )

    logger.info(
        f"Scanner configured: intraday every {settings.scan_interval_intraday_seconds}s, "
        f"long-term every {settings.scan_interval_longterm_seconds}s, "
        f"exit alerts every {settings.scan_interval_intraday_seconds}s, "
        f"alert purge daily at 15:35 IST"
    )

    return scheduler
