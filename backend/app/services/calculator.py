"""Break-even and target exit price calculator.

Factors in all Indian statutory charges (brokerage, STT, exchange fees,
stamp duty, GST, SEBI fee) for both intraday and delivery trades.
"""

import logging
from app.utils.charges import calc_charges_intraday, calc_charges_delivery

logger = logging.getLogger(__name__)


def calculate_breakeven(
    trade_type: str,
    direction: str,
    quantity: int,
    entry_price: float,
    target_profit: float | None = None,
) -> dict:
    """
    Calculate break-even exit price (and optional target exit price) for a trade.

    For a BUY trade:
      - Buy charges are computed on entry_price × quantity.
      - We solve for exit_price such that:
        sell_proceeds - sell_charges = total_buy_cost [+ target_profit]

    For a SELL (short) trade:
      - Sell entry charges are computed on entry_price × quantity.
      - We solve for exit_price (buy-to-cover) such that:
        sell_proceeds - buy_cover_cost = target [break-even or profit]

    Args:
        trade_type: "intraday", "short_selling", or "long_term".
        direction: "BUY" or "SELL".
        quantity: Number of shares.
        entry_price: Price per share at entry.
        target_profit: Optional profit target in ₹.

    Returns:
        Dict with breakeven price, target price, and full charge breakdown.
    """
    is_delivery = trade_type == "long_term"
    calc_fn = calc_charges_delivery if is_delivery else calc_charges_intraday

    buy_value = entry_price * quantity

    if direction == "BUY":
        # Entry is buy side
        charges_buy = calc_fn(buy_value, "BUY")
        total_cost = buy_value + charges_buy["total"]

        # Solve for breakeven exit price
        # At exit (sell side): sell_value - sell_charges = total_cost
        # sell_charges are a function of sell_value, so we solve iteratively
        breakeven_price = _solve_exit_price(
            quantity, total_cost, 0.0, calc_fn, "SELL"
        )

        # Solve for target exit price
        target_price = None
        if target_profit is not None and target_profit > 0:
            target_price = _solve_exit_price(
                quantity, total_cost, target_profit, calc_fn, "SELL"
            )

        # Calculate charges at breakeven for the response
        be_sell_value = breakeven_price * quantity
        charges_sell = calc_fn(be_sell_value, "SELL")

        return {
            "entry_price": round(entry_price, 2),
            "quantity": quantity,
            "trade_type": trade_type,
            "direction": direction,
            "buy_value": round(buy_value, 2),
            "sell_value_breakeven": round(be_sell_value, 2),
            "breakeven_price": round(breakeven_price, 2),
            "target_price": round(target_price, 2) if target_price else None,
            "total_charges_buy": charges_buy["total"],
            "total_charges_sell": charges_sell["total"],
            "charges_breakdown_buy": charges_buy,
            "charges_breakdown_sell": charges_sell,
            "net_profit": 0.0 if target_profit is None else round(target_profit, 2),
        }

    else:
        # direction == "SELL" (short selling)
        # Entry is sell side (we receive money)
        charges_sell_entry = calc_fn(buy_value, "SELL")
        net_sell_proceeds = buy_value - charges_sell_entry["total"]

        # Solve for breakeven buy-to-cover price
        # At cover (buy side): buy_value + buy_charges = net_sell_proceeds
        breakeven_price = _solve_cover_price(
            quantity, net_sell_proceeds, 0.0, calc_fn, "BUY"
        )

        target_price = None
        if target_profit is not None and target_profit > 0:
            target_price = _solve_cover_price(
                quantity, net_sell_proceeds, target_profit, calc_fn, "BUY"
            )

        be_buy_value = breakeven_price * quantity
        charges_buy_cover = calc_fn(be_buy_value, "BUY")

        return {
            "entry_price": round(entry_price, 2),
            "quantity": quantity,
            "trade_type": trade_type,
            "direction": direction,
            "buy_value": round(buy_value, 2),
            "sell_value_breakeven": round(be_buy_value, 2),
            "breakeven_price": round(breakeven_price, 2),
            "target_price": round(target_price, 2) if target_price else None,
            "total_charges_buy": charges_buy_cover["total"],
            "total_charges_sell": charges_sell_entry["total"],
            "charges_breakdown_buy": charges_buy_cover,
            "charges_breakdown_sell": charges_sell_entry,
            "net_profit": 0.0 if target_profit is None else round(target_profit, 2),
        }


def _solve_exit_price(
    quantity: int,
    total_cost: float,
    target_profit: float,
    calc_fn,
    exit_side: str,
    max_iterations: int = 50,
    tolerance: float = 0.005,
) -> float:
    """
    Iteratively solve for the exit price where:
    exit_value - exit_charges = total_cost + target_profit

    Uses Newton-like bisection starting from a reasonable estimate.
    """
    required = total_cost + target_profit

    # Initial estimate: assume ~0.1% total friction
    estimate = required / quantity * 1.002

    for _ in range(max_iterations):
        exit_value = estimate * quantity
        charges = calc_fn(exit_value, exit_side)
        net = exit_value - charges["total"]
        error = net - required

        if abs(error) < tolerance:
            return estimate

        # Adjust: if net is too low, increase price; if too high, decrease
        # Approximate gradient: d(net)/d(price) ≈ quantity * (1 - charge_rate)
        charge_rate = charges["total"] / exit_value if exit_value > 0 else 0.001
        gradient = quantity * (1 - charge_rate)
        if gradient > 0:
            estimate -= error / gradient
        else:
            estimate *= 1.001

    return estimate


def _solve_cover_price(
    quantity: int,
    net_proceeds: float,
    target_profit: float,
    calc_fn,
    cover_side: str,
    max_iterations: int = 50,
    tolerance: float = 0.005,
) -> float:
    """
    For short trades: solve for cover price where:
    cover_value + cover_charges = net_proceeds - target_profit

    The cover (buy-to-close) price should be lower than entry for profit.
    """
    budget = net_proceeds - target_profit

    # Initial estimate
    estimate = budget / quantity * 0.998

    for _ in range(max_iterations):
        cover_value = estimate * quantity
        charges = calc_fn(cover_value, cover_side)
        total_cover_cost = cover_value + charges["total"]
        error = total_cover_cost - budget

        if abs(error) < tolerance:
            return estimate

        charge_rate = charges["total"] / cover_value if cover_value > 0 else 0.001
        gradient = quantity * (1 + charge_rate)
        if gradient > 0:
            estimate -= error / gradient
        else:
            estimate *= 0.999

    return estimate
