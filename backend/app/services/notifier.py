"""Telegram notification dispatcher for confluence alerts."""

import logging
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Telegram Bot API base URL
_TG_API = "https://api.telegram.org/bot{token}/sendMessage"


async def send_telegram_alert(
    ticker: str,
    mode: str,
    price: float,
    details: dict,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> bool:
    """
    Send a formatted confluence alert via Telegram Bot.

    Args:
        ticker: Stock symbol.
        mode: Trading mode ("intraday", "short_selling", "long_term").
        price: Current price at alert time.
        details: Dict with per-indicator detail strings.
        bot_token: Telegram bot token (falls back to settings).
        chat_id: Telegram chat ID (falls back to settings).

    Returns:
        True if message sent successfully.
    """
    settings = get_settings()
    token = bot_token or settings.telegram_bot_token
    chat = chat_id or settings.telegram_chat_id

    if not token or not chat or token == "your-bot-token-here":
        logger.warning("Telegram not configured — skipping notification")
        return False

    # Format mode display
    mode_labels = {
        "intraday": "📈 INTRADAY (Buy Side)",
        "short_selling": "📉 SHORT SELLING (Sell Side)",
        "long_term": "🏦 LONG-TERM (Delivery)",
    }

    mode_label = mode_labels.get(mode, mode.upper())

    # Build message
    lines = [
        f"🎯 *CONFLUENCE ALERT*",
        f"",
        f"*{ticker}* — ₹{price:.2f}",
        f"Mode: {mode_label}",
        f"",
        f"*Indicator Alignment:*",
    ]

    for key, detail in details.items():
        emoji = "✅" if "✓" in detail or ">" in detail or "Bullish" in detail or "rising" in detail else "🔴"
        lines.append(f"{emoji} {detail}")

    lines.extend([
        f"",
        f"⚠️ _This is an educational alert, not financial advice._",
    ])

    message = "\n".join(lines)

    try:
        url = _TG_API.format(token=token)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "chat_id": chat,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
                timeout=10.0,
            )

        if response.status_code == 200:
            logger.info(f"Telegram alert sent for {ticker} ({mode})")
            return True
        else:
            logger.error(
                f"Telegram API error {response.status_code}: {response.text}"
            )
            return False

    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        return False

async def test_telegram_connection(
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> dict:
    """Send a test message to verify Telegram configuration."""
    settings = get_settings()
    token = bot_token or settings.telegram_bot_token
    chat = chat_id or settings.telegram_chat_id

    if not token or not chat:
        return {"success": False, "error": "Bot token or chat ID not configured"}

    try:
        url = _TG_API.format(token=token)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "chat_id": chat,
                    "text": "✅ TradingHelper connected successfully!\n\nYou will receive confluence alerts here.",
                    "parse_mode": "Markdown",
                },
                timeout=10.0,
            )

        if response.status_code == 200:
            return {"success": True, "message": "Test message sent!"}
        else:
            return {"success": False, "error": f"API error: {response.text}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def send_ntfy_alert(
    ticker: str,
    mode: str,
    price: float,
    details: dict,
    topic: Optional[str] = None,
) -> bool:
    """
    Send a formatted confluence alert via ntfy.sh push notification.

    Args:
        ticker: Stock symbol.
        mode: Trading mode ("intraday", "short_selling", "long_term").
        price: Current price at alert time.
        details: Dict with per-indicator detail strings.
        topic: Secret ntfy topic (falls back to settings).

    Returns:
        True if push notification sent successfully.
    """
    settings = get_settings()
    ntfy_topic = (topic.strip() if topic else None) or settings.ntfy_topic

    if not ntfy_topic:
        logger.warning("Ntfy topic not configured — skipping ntfy notification")
        return False

    mode_labels = {
        "intraday": "Intraday (Buy Side)",
        "short_selling": "Short Selling (Sell Side)",
        "long_term": "Long-Term (Delivery)",
    }
    mode_label = mode_labels.get(mode, mode.upper())

    # Build message body showing all 4 indicator confluences
    lines = [
        f"Stock: {ticker}",
        f"Price: ₹{price:.2f}",
        f"Mode: {mode_label}",
        f"Confluence: ALL 4 INDICATORS ALIGNED",
        "",
        "Alignment Breakdown:",
    ]
    for key, detail in details.items():
        lines.append(f"• {detail}")

    lines.append("\n⚠️ Educational alert only. Not financial advice.")
    message = "\n".join(lines)

    tags = "chart_with_upwards_trend,bullseye" if mode != "short_selling" else "chart_with_downwards_trend,bullseye"
    title = f"CONFLUENCE ALERT: {ticker} ({mode_label})"

    try:
        url = f"https://ntfy.sh/{ntfy_topic.strip()}"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                content=message.encode("utf-8"),
                headers={
                    "Title": title,
                    "Priority": "4",
                    "Tags": tags,
                },
                timeout=10.0,
            )

        if response.status_code == 200:
            logger.info(f"Ntfy alert sent for {ticker} ({mode}) to topic {ntfy_topic}")
            return True
        else:
            logger.error(f"Ntfy API error {response.status_code}: {response.text}")
            return False

    except Exception as e:
        logger.error(f"Failed to send Ntfy alert: {e}")
        return False


async def test_ntfy_connection(topic: Optional[str] = None) -> dict:
    """Send a test push notification to verify Ntfy configuration."""
    settings = get_settings()
    ntfy_topic = (topic.strip() if topic else None) or settings.ntfy_topic

    if not ntfy_topic:
        return {"success": False, "error": "Ntfy topic not configured"}

    try:
        url = f"https://ntfy.sh/{ntfy_topic.strip()}"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                content="✅ TradingHelper connected! You will receive 4-indicator confluence alerts on this device.".encode("utf-8"),
                headers={
                    "Title": "TradingHelper Alert Test",
                    "Priority": "3",
                    "Tags": "white_check_mark,tada",
                },
                timeout=10.0,
            )

        if response.status_code == 200:
            return {"success": True, "message": "Test notification sent!"}
        else:
            return {"success": False, "error": f"Ntfy error: {response.text}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Exit Alert Notifiers ───────────────────────────────────────────────────────

async def send_exit_telegram_alert(
    ticker: str,
    alert_type: str,
    alert_category: str,
    reason: str,
    price: float,
    net_pnl: float,
    trade_direction: str,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> bool:
    """
    Send a formatted exit alert (Stop-Loss or Take-Profit) via Telegram Bot.

    Args:
        ticker: Stock symbol (e.g. "RELIANCE").
        alert_type: Short label for the signal (e.g. "VWAP Breakdown").
        alert_category: "exit_stoploss" | "exit_takeprofit".
        reason: Human-readable explanation of why the alert fired.
        price: Current market price at alert time.
        net_pnl: Unrealised net PnL after estimated fees.
        trade_direction: "INTRADAY_BUY" | "SHORT_SELL" | "LONG_TERM".
        bot_token: Telegram bot token (falls back to settings).
        chat_id: Telegram chat ID (falls back to settings).

    Returns:
        True if the message was sent successfully.
    """
    settings = get_settings()
    token = bot_token or settings.telegram_bot_token
    chat = chat_id or settings.telegram_chat_id

    if not token or not chat or token == "your-bot-token-here":
        logger.warning("Telegram not configured — skipping exit alert notification")
        return False

    is_stoploss = alert_category == "exit_stoploss"
    category_emoji = "🔴" if is_stoploss else "💰"
    category_label = "STOP-LOSS WARNING" if is_stoploss else "TAKE-PROFIT SIGNAL"

    direction_labels = {
        "INTRADAY_BUY": "LONG (Intraday Buy)",
        "SHORT_SELL": "SHORT (Short Sell)",
        "LONG_TERM": "LONG (Long-Term CNC)",
    }
    direction_label = direction_labels.get(trade_direction, trade_direction)

    pnl_prefix = "+" if net_pnl >= 0 else ""
    pnl_emoji = "🟢" if net_pnl >= 0 else "🔴"

    lines = [
        f"🚨 *[EXIT ALERT]* {ticker} — {alert_type}",
        f"",
        f"Type: {category_emoji} *{category_label}*",
        f"Direction: {direction_label}",
        f"",
        f"📋 *Reason:* {reason}",
        f"💵 *Current Price:* ₹{price:.2f}",
        f"{pnl_emoji} *Unrealised Net PnL:* ₹{pnl_prefix}{net_pnl:.2f}",
        f"",
        f"⚠️ _Educational alert only\\. Not financial advice\\._",
    ]

    message = "\n".join(lines)

    try:
        url = _TG_API.format(token=token)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "chat_id": chat,
                    "text": message,
                    "parse_mode": "MarkdownV2",
                    "disable_web_page_preview": True,
                },
                timeout=10.0,
            )

        if response.status_code == 200:
            logger.info(f"Exit Telegram alert sent: {ticker} — {alert_type}")
            return True
        else:
            logger.error(
                f"Telegram API error for exit alert {response.status_code}: {response.text}"
            )
            return False

    except Exception as e:
        logger.error(f"Failed to send exit Telegram alert: {e}")
        return False


async def send_exit_ntfy_alert(
    ticker: str,
    alert_type: str,
    alert_category: str,
    reason: str,
    price: float,
    net_pnl: float,
    trade_direction: str,
    topic: Optional[str] = None,
) -> bool:
    """
    Send a formatted exit alert (Stop-Loss or Take-Profit) via ntfy.sh.

    Args:
        ticker: Stock symbol (e.g. "RELIANCE").
        alert_type: Short label for the signal (e.g. "VWAP Breakdown").
        alert_category: "exit_stoploss" | "exit_takeprofit".
        reason: Human-readable explanation of why the alert fired.
        price: Current market price at alert time.
        net_pnl: Unrealised net PnL after estimated fees.
        trade_direction: "INTRADAY_BUY" | "SHORT_SELL" | "LONG_TERM".
        topic: ntfy topic (falls back to settings).

    Returns:
        True if the push notification was sent successfully.
    """
    settings = get_settings()
    ntfy_topic = (topic.strip() if topic else None) or settings.ntfy_topic

    if not ntfy_topic:
        logger.warning("Ntfy topic not configured — skipping exit alert notification")
        return False

    is_stoploss = alert_category == "exit_stoploss"

    # Higher priority (5 = max) for stop-loss, standard (4) for take-profit
    priority = "5" if is_stoploss else "4"

    # Distinct emoji tags so exit alerts look different from entry alerts
    if is_stoploss:
        tags = "warning,rotating_light"
    else:
        tags = "moneybag,chart_with_upwards_trend"

    pnl_prefix = "+" if net_pnl >= 0 else ""

    direction_labels = {
        "INTRADAY_BUY": "LONG Intraday",
        "SHORT_SELL": "SHORT Sell",
        "LONG_TERM": "LONG CNC",
    }
    direction_label = direction_labels.get(trade_direction, trade_direction)

    title = f"[EXIT ALERT] {ticker} - {alert_type}"

    body_lines = [
        f"Direction: {direction_label}",
        f"Reason: {reason}",
        f"Current Price: Rs{price:.2f}",
        f"Unrealised Net PnL: Rs{pnl_prefix}{net_pnl:.2f}",
        "",
        "Educational alert only. Not financial advice.",
    ]
    body = "\n".join(body_lines)

    try:
        url = f"https://ntfy.sh/{ntfy_topic.strip()}"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                content=body.encode("utf-8"),
                headers={
                    "Title": title,
                    "Priority": priority,
                    "Tags": tags,
                },
                timeout=10.0,
            )

        if response.status_code == 200:
            logger.info(f"Exit ntfy alert sent: {ticker} — {alert_type}")
            return True
        else:
            logger.error(f"Ntfy exit alert error {response.status_code}: {response.text}")
            return False

    except Exception as e:
        logger.error(f"Failed to send exit ntfy alert: {e}")
        return False

