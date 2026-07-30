"""Conditional Exit Alert Engine.

Scans ALL open paper trades on every scheduler tick and evaluates
exit conditions (Stop-Loss & Take-Profit) using live indicator data.

Rules evaluated:
    LONG (INTRADAY_BUY / LONG_TERM):
        Stop-Loss  -> VWAP Breakdown, Supertrend Flip, Hard SL Hit
        Take-Profit -> RSI > 70, MACD Bearish Crossover, Break-Even Reached

    SHORT (SHORT_SELL):
        Stop-Loss  -> VWAP Breakout, Supertrend Flip, Hard SL Hit
        Take-Profit -> RSI < 30, MACD Bullish Crossover

Each condition sends one notification per trigger state via Telegram
and ntfy, then sets a boolean flag on the PaperTrade row to prevent
spam. Flags are cleared when the condition resolves, enabling re-alert
on a fresh trigger.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import _get_session_maker
from app.models import AlertHistory, AppSettings, PaperTrade
from app.services.data_fetcher import fetch_ohlcv
from app.services.indicators import IndicatorResult, calculate_indicators
from app.services.notifier import send_exit_ntfy_alert, send_exit_telegram_alert
from app.utils.charges import calc_charges_delivery, calc_charges_intraday

logger = logging.getLogger(__name__)


# == Helpers ===================================================================

def _trade_mode(trade: PaperTrade) -> str:
    """Map trade_direction to the indicator-calculation mode string."""
    if trade.trade_direction == "INTRADAY_BUY":
        return "intraday"
    elif trade.trade_direction == "SHORT_SELL":
        return "short_selling"
    else:
        return "long_term"


def _calc_net_pnl(trade: PaperTrade, current_price: float) -> float:
    """Calculate current unrealised net PnL (after estimated fees) for an open trade."""
    is_delivery = trade.trade_direction == "LONG_TERM"
    calc_fn = calc_charges_delivery if is_delivery else calc_charges_intraday

    entry_turnover = trade.entry_price * trade.quantity
    exit_turnover = current_price * trade.quantity

    if trade.trade_direction in ("INTRADAY_BUY", "LONG_TERM"):
        pnl_gross = (current_price - trade.entry_price) * trade.quantity
        entry_fees = calc_fn(entry_turnover, "BUY")["total"]
        exit_fees = calc_fn(exit_turnover, "SELL")["total"]
    else:  # SHORT_SELL
        pnl_gross = (trade.entry_price - current_price) * trade.quantity
        entry_fees = calc_fn(entry_turnover, "SELL")["total"]
        exit_fees = calc_fn(exit_turnover, "BUY")["total"]

    return round(pnl_gross - entry_fees - exit_fees, 2)


def _effective_sl(trade: PaperTrade) -> float:
    """Return the effective stop-loss level: user-defined takes priority."""
    if trade.user_defined_stop_loss is not None:
        return trade.user_defined_stop_loss
    return trade.suggested_stop_loss_price


# == Notification dispatcher ===================================================

async def _fire_exit_alert(
    trade: PaperTrade,
    alert_type: str,
    alert_category: str,
    reason: str,
    current_price: float,
    net_pnl: float,
    settings_map: dict,
    session: AsyncSession,
) -> None:
    """Send Telegram + ntfy exit alert and log to AlertHistory."""
    logger.info(
        "EXIT ALERT [%s] %s -- %s | price=Rs%.2f | NetPnL=Rs%.2f",
        alert_category.upper(), trade.ticker, alert_type, current_price, net_pnl,
    )

    ntfy_topic = settings_map.get("ntfy_topic")
    tg_token = settings_map.get("telegram_bot_token")
    tg_chat = settings_map.get("telegram_chat_id")

    tg_sent = await send_exit_telegram_alert(
        ticker=trade.ticker,
        alert_type=alert_type,
        alert_category=alert_category,
        reason=reason,
        price=current_price,
        net_pnl=net_pnl,
        trade_direction=trade.trade_direction,
        bot_token=tg_token,
        chat_id=tg_chat,
    )

    ntfy_sent = await send_exit_ntfy_alert(
        ticker=trade.ticker,
        alert_type=alert_type,
        alert_category=alert_category,
        reason=reason,
        price=current_price,
        net_pnl=net_pnl,
        trade_direction=trade.trade_direction,
        topic=ntfy_topic,
    )

    notified_methods = []
    if tg_sent:
        notified_methods.append("telegram")
    if ntfy_sent:
        notified_methods.append("ntfy")

    try:
        alert = AlertHistory(
            user_id=trade.user_id,
            ticker=trade.ticker,
            mode=_trade_mode(trade),
            alert_type=alert_category,
            indicator_data={
                "exit_signal": alert_type,
                "reason": reason,
                "price": current_price,
                "net_pnl": net_pnl,
                "trade_id": trade.id,
                "trade_direction": trade.trade_direction,
            },
            price_at_alert=current_price,
            notified_via=",".join(notified_methods) if notified_methods else "none",
        )
        session.add(alert)
    except Exception as exc:
        logger.error("Failed to log exit alert to AlertHistory: %s", exc)


# == LONG trade evaluator ======================================================

async def _evaluate_long_exit(
    trade: PaperTrade,
    ind: IndicatorResult,
    session: AsyncSession,
    settings_map: dict,
) -> None:
    """
    Evaluate exit conditions for a LONG trade (INTRADAY_BUY or LONG_TERM).

    Stop-Loss:
        - VWAP Breakdown (intraday only): close < vwap
        - Supertrend Flip to Bearish: live direction == -1
        - Hard Stop-Loss Hit: price < effective SL

    Take-Profit:
        - RSI Overbought > 70
        - MACD Bearish Crossover
        - Break-Even Reached (one-shot, flag never resets)
    """
    price = ind.price
    net_pnl = _calc_net_pnl(trade, price)
    changed = False

    # 1. VWAP Breakdown (intraday / short_selling modes only)
    if ind.vwap is not None:
        vwap_breakdown = price < ind.vwap
        if vwap_breakdown and not trade.exit_alert_vwap_sent:
            await _fire_exit_alert(
                trade, "VWAP Breakdown", "exit_stoploss",
                f"Current candle closed BELOW VWAP Rs{ind.vwap:.2f}",
                price, net_pnl, settings_map, session,
            )
            trade.exit_alert_vwap_sent = True
            changed = True
        elif not vwap_breakdown and trade.exit_alert_vwap_sent:
            trade.exit_alert_vwap_sent = False
            changed = True

    # 2. Supertrend Flip to Bearish
    supertrend_bearish = ind.supertrend_direction == -1
    if supertrend_bearish and not trade.exit_alert_supertrend_sent:
        await _fire_exit_alert(
            trade, "Supertrend Reversal", "exit_stoploss",
            f"Supertrend flipped to Bearish (Red) at Rs{ind.supertrend_value:.2f}",
            price, net_pnl, settings_map, session,
        )
        trade.exit_alert_supertrend_sent = True
        changed = True
    elif not supertrend_bearish and trade.exit_alert_supertrend_sent:
        trade.exit_alert_supertrend_sent = False
        changed = True

    # 3. Hard Stop-Loss Hit
    sl_level = _effective_sl(trade)
    sl_hit = price < sl_level
    if sl_hit and not trade.exit_alert_stoploss_sent:
        await _fire_exit_alert(
            trade, "Stop-Loss Hit", "exit_stoploss",
            f"Price Rs{price:.2f} dropped below Stop-Loss Rs{sl_level:.2f}",
            price, net_pnl, settings_map, session,
        )
        trade.exit_alert_stoploss_sent = True
        changed = True
    elif not sl_hit and trade.exit_alert_stoploss_sent:
        trade.exit_alert_stoploss_sent = False
        changed = True

    # 4. RSI Overbought (> 70)
    rsi_overbought = ind.rsi > 70
    if rsi_overbought and not trade.exit_alert_rsi_sent:
        await _fire_exit_alert(
            trade, "RSI Overbought Peak", "exit_takeprofit",
            f"RSI {ind.rsi:.1f} crossed above 70 -- momentum overextended, pullback likely",
            price, net_pnl, settings_map, session,
        )
        trade.exit_alert_rsi_sent = True
        changed = True
    elif not rsi_overbought and trade.exit_alert_rsi_sent:
        trade.exit_alert_rsi_sent = False
        changed = True

    # 5. MACD Bearish Crossover
    macd_bearish_cross = ind.macd_crossover == "bearish"
    if macd_bearish_cross and not trade.exit_alert_macd_sent:
        await _fire_exit_alert(
            trade, "MACD Bearish Crossover", "exit_takeprofit",
            f"MACD ({ind.macd_line:.4f}) crossed below Signal ({ind.macd_signal:.4f}) -- upward momentum fading",
            price, net_pnl, settings_map, session,
        )
        trade.exit_alert_macd_sent = True
        changed = True
    elif not macd_bearish_cross and trade.exit_alert_macd_sent:
        trade.exit_alert_macd_sent = False
        changed = True

    # 6. Break-Even Reached (one-shot, flag never resets)
    be_reached = price >= trade.calculated_break_even_price
    if be_reached and not trade.exit_alert_breakeven_sent:
        await _fire_exit_alert(
            trade, "Break-Even Reached", "exit_takeprofit",
            f"Price Rs{price:.2f} crossed Break-Even Rs{trade.calculated_break_even_price:.2f} -- trade is now net profitable after fees!",
            price, net_pnl, settings_map, session,
        )
        trade.exit_alert_breakeven_sent = True
        changed = True

    if changed:
        await session.commit()


# == SHORT trade evaluator =====================================================

async def _evaluate_short_exit(
    trade: PaperTrade,
    ind: IndicatorResult,
    session: AsyncSession,
    settings_map: dict,
) -> None:
    """
    Evaluate exit conditions for a SHORT trade (SHORT_SELL).

    Stop-Loss:
        - VWAP Breakout: close > vwap
        - Supertrend Flip to Bullish: live direction == 1
        - Hard Stop-Loss Hit: price > effective SL

    Take-Profit:
        - RSI Oversold < 30
        - MACD Bullish Crossover
    """
    price = ind.price
    net_pnl = _calc_net_pnl(trade, price)
    changed = False

    # 1. VWAP Breakout
    if ind.vwap is not None:
        vwap_breakout = price > ind.vwap
        if vwap_breakout and not trade.exit_alert_vwap_sent:
            await _fire_exit_alert(
                trade, "VWAP Breakout", "exit_stoploss",
                f"Current candle closed ABOVE VWAP Rs{ind.vwap:.2f} -- short momentum lost",
                price, net_pnl, settings_map, session,
            )
            trade.exit_alert_vwap_sent = True
            changed = True
        elif not vwap_breakout and trade.exit_alert_vwap_sent:
            trade.exit_alert_vwap_sent = False
            changed = True

    # 2. Supertrend Flip to Bullish
    supertrend_bullish = ind.supertrend_direction == 1
    if supertrend_bullish and not trade.exit_alert_supertrend_sent:
        await _fire_exit_alert(
            trade, "Supertrend Reversal", "exit_stoploss",
            f"Supertrend flipped to Bullish (Green) at Rs{ind.supertrend_value:.2f} -- cover your short",
            price, net_pnl, settings_map, session,
        )
        trade.exit_alert_supertrend_sent = True
        changed = True
    elif not supertrend_bullish and trade.exit_alert_supertrend_sent:
        trade.exit_alert_supertrend_sent = False
        changed = True

    # 3. Hard Stop-Loss Hit (for a short, SL is ABOVE entry)
    sl_level = _effective_sl(trade)
    sl_hit = price > sl_level
    if sl_hit and not trade.exit_alert_stoploss_sent:
        await _fire_exit_alert(
            trade, "Stop-Loss Hit", "exit_stoploss",
            f"Price Rs{price:.2f} rose above Stop-Loss Rs{sl_level:.2f}",
            price, net_pnl, settings_map, session,
        )
        trade.exit_alert_stoploss_sent = True
        changed = True
    elif not sl_hit and trade.exit_alert_stoploss_sent:
        trade.exit_alert_stoploss_sent = False
        changed = True

    # 4. RSI Oversold (< 30)
    rsi_oversold = ind.rsi < 30
    if rsi_oversold and not trade.exit_alert_rsi_sent:
        await _fire_exit_alert(
            trade, "RSI Oversold Trough", "exit_takeprofit",
            f"RSI {ind.rsi:.1f} dropped below 30 -- extreme selling, short-covering bounce risk",
            price, net_pnl, settings_map, session,
        )
        trade.exit_alert_rsi_sent = True
        changed = True
    elif not rsi_oversold and trade.exit_alert_rsi_sent:
        trade.exit_alert_rsi_sent = False
        changed = True

    # 5. MACD Bullish Crossover
    macd_bullish_cross = ind.macd_crossover == "bullish"
    if macd_bullish_cross and not trade.exit_alert_macd_sent:
        await _fire_exit_alert(
            trade, "MACD Bullish Crossover", "exit_takeprofit",
            f"MACD ({ind.macd_line:.4f}) crossed above Signal ({ind.macd_signal:.4f}) -- downward momentum lost",
            price, net_pnl, settings_map, session,
        )
        trade.exit_alert_macd_sent = True
        changed = True
    elif not macd_bullish_cross and trade.exit_alert_macd_sent:
        trade.exit_alert_macd_sent = False
        changed = True

    if changed:
        await session.commit()


# == Main scan entry point =====================================================

async def scan_open_trades_for_exits() -> None:
    """
    Top-level coroutine called by APScheduler on every intraday tick.

    1. Fetches all OPEN paper trades from DB. Exits immediately if none.
    2. Loads app settings (Telegram/ntfy credentials) once for the batch.
    3. For each trade, fetches live OHLCV + calculates indicators.
    4. Delegates to the LONG or SHORT exit evaluator.
    """
    try:
        async with _get_session_maker()() as session:
            result = await session.execute(
                select(PaperTrade).where(PaperTrade.status == "OPEN")
            )
            open_trades: list[PaperTrade] = result.scalars().all()

        if not open_trades:
            logger.debug("Exit scanner: no open paper trades -- skipping.")
            return

        logger.info("Exit scanner: evaluating %d open trade(s)...", len(open_trades))

        # Load settings once per batch
        settings_map: dict = {}
        try:
            async with _get_session_maker()() as s:
                st_res = await s.execute(select(AppSettings))
                settings_map = {r.key: r.value for r in st_res.scalars().all()}
        except Exception as exc:
            logger.warning("Exit scanner: could not load app settings: %s", exc)

        for trade in open_trades:
            try:
                await _scan_single_trade(trade, settings_map)
            except Exception as exc:
                logger.error(
                    "Exit scanner: error evaluating %s (id=%s): %s",
                    trade.ticker, trade.id, exc,
                    exc_info=True,
                )

    except Exception as exc:
        logger.error("Exit scanner: fatal error in scan loop: %s", exc, exc_info=True)


async def _scan_single_trade(trade: PaperTrade, settings_map: dict) -> None:
    """Fetch live indicators and evaluate exit rules for one open trade."""
    mode = _trade_mode(trade)

    if mode in ("intraday", "short_selling"):
        interval, period = "5m", "5d"
    else:
        interval, period = "1d", "1y"

    df = fetch_ohlcv(trade.ticker, interval=interval, period=period)
    if df.empty:
        logger.warning("Exit scanner: no OHLCV data for %s", trade.ticker)
        return

    ind = calculate_indicators(df, mode=mode)
    if ind is None:
        logger.warning("Exit scanner: insufficient data for indicators: %s", trade.ticker)
        return

    logger.debug(
        "Exit scanner: %s (%s) price=Rs%.2f rsi=%.1f macd_cross=%s st_dir=%d",
        trade.ticker, trade.trade_direction,
        ind.price, ind.rsi, ind.macd_crossover, ind.supertrend_direction,
    )

    # Use a fresh session per trade so flag commits are isolated
    async with _get_session_maker()() as session:
        # Re-fetch inside this session to enable dirty writes
        live_trade = await session.get(PaperTrade, trade.id)
        if live_trade is None or live_trade.status != "OPEN":
            return  # Race-condition guard: trade was just closed

        if live_trade.trade_direction in ("INTRADAY_BUY", "LONG_TERM"):
            await _evaluate_long_exit(live_trade, ind, session, settings_map)
        else:
            await _evaluate_short_exit(live_trade, ind, session, settings_map)
