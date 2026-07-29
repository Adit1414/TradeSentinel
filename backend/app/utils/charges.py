"""Indian statutory trading charges constants and calculation helpers.

All rates are sourced from standard NSE/SEBI/Government regulations as of 2025.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class IntradayCharges:
    """Charge rates for Intraday (MIS) and Short Selling trades."""
    brokerage_pct: float = 0.03          # 0.03% of turnover per leg
    stt_sell_pct: float = 0.025          # 0.025% on sell side only
    exchange_txn_pct: float = 0.00297    # NSE exchange transaction charge
    stamp_duty_buy_pct: float = 0.003    # Stamp duty on buy side only
    gst_pct: float = 18.0               # 18% GST on (brokerage + exchange txn)
    sebi_per_crore: float = 10.0         # ₹10 per crore of turnover


@dataclass(frozen=True)
class DeliveryCharges:
    """Charge rates for Long-Term / CNC / Delivery trades."""
    brokerage_pct: float = 0.0           # Zero brokerage (most discount brokers)
    stt_pct: float = 0.1                 # 0.1% on BOTH buy and sell
    exchange_txn_pct: float = 0.00297    # NSE exchange transaction charge
    stamp_duty_buy_pct: float = 0.015    # Stamp duty on buy side only
    gst_pct: float = 18.0               # 18% GST on (brokerage + exchange txn)
    sebi_per_crore: float = 10.0         # ₹10 per crore of turnover


INTRADAY_CHARGES = IntradayCharges()
DELIVERY_CHARGES = DeliveryCharges()


def calc_charges_intraday(turnover: float, side: str) -> dict:
    """
    Calculate all statutory charges for one leg of an intraday trade.

    Args:
        turnover: Price × Quantity for this leg.
        side: "BUY" or "SELL".

    Returns:
        Dict with itemized charges and total.
    """
    c = INTRADAY_CHARGES
    brokerage = turnover * (c.brokerage_pct / 100)
    stt = turnover * (c.stt_sell_pct / 100) if side == "SELL" else 0.0
    exchange_txn = turnover * (c.exchange_txn_pct / 100)
    stamp_duty = turnover * (c.stamp_duty_buy_pct / 100) if side == "BUY" else 0.0
    gst = (brokerage + exchange_txn) * (c.gst_pct / 100)
    sebi_fee = turnover * (c.sebi_per_crore / 1e7)  # ₹10 per crore = 10/10^7

    total = brokerage + stt + exchange_txn + stamp_duty + gst + sebi_fee

    return {
        "brokerage": round(brokerage, 2),
        "stt": round(stt, 2),
        "exchange_txn": round(exchange_txn, 2),
        "stamp_duty": round(stamp_duty, 2),
        "gst": round(gst, 2),
        "sebi_fee": round(sebi_fee, 4),
        "total": round(total, 2),
    }


def calc_charges_delivery(turnover: float, side: str) -> dict:
    """
    Calculate all statutory charges for one leg of a delivery/CNC trade.

    Args:
        turnover: Price × Quantity for this leg.
        side: "BUY" or "SELL".

    Returns:
        Dict with itemized charges and total.
    """
    c = DELIVERY_CHARGES
    brokerage = turnover * (c.brokerage_pct / 100)
    stt = turnover * (c.stt_pct / 100)  # Applied on both sides for delivery
    exchange_txn = turnover * (c.exchange_txn_pct / 100)
    stamp_duty = turnover * (c.stamp_duty_buy_pct / 100) if side == "BUY" else 0.0
    gst = (brokerage + exchange_txn) * (c.gst_pct / 100)
    sebi_fee = turnover * (c.sebi_per_crore / 1e7)

    total = brokerage + stt + exchange_txn + stamp_duty + gst + sebi_fee

    return {
        "brokerage": round(brokerage, 2),
        "stt": round(stt, 2),
        "exchange_txn": round(exchange_txn, 2),
        "stamp_duty": round(stamp_duty, 2),
        "gst": round(gst, 2),
        "sebi_fee": round(sebi_fee, 4),
        "total": round(total, 2),
    }
