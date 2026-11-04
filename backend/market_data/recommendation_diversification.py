"""Concentration-capped whole-share *paper* allocation for research shortlists.

Unlike the legacy rank-first allocator, this design will not place the entire
budget in a top-ranked stock. These policy caps are conservative examples,
NOT empirically optimized weights, and are not personalized financial advice.
"""
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_FLOOR

# Explicit illustrative policy, not inferred from forecast skill.
CAPS = {
    "low": (Decimal("0.15"), Decimal("0.35")),
    "moderate": (Decimal("0.25"), Decimal("0.50")),
    "high": (Decimal("0.35"), Decimal("0.65")),
}


def _amount(value):
    if isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return result if result.is_finite() else None


def allocate_diversified_shares(candidates, *, budget, currency,
                                max_allocations=10, risk_tolerance="moderate"):
    """Rank-aware allocation with explicit position/sector ceilings.

    Seed one affordable whole share into each candidate first, then fill
    remaining room by rank, preserving a cash balance if limits bind.
    No currency conversions, fractional shares or leveraged investments.
    """
    funds = _amount(budget)
    if funds is None or funds <= 0:
        raise ValueError("Budget must be a positive finite amount.")
    currency = str(currency).strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", currency, flags=re.ASCII):
        raise ValueError("Currency must be a three-letter ISO-like code.")
    if type(max_allocations) is not int or not 1 <= max_allocations <= 100:
        raise ValueError("max_allocations must be an integer between 1 and 100.")
    if risk_tolerance not in CAPS:
        raise ValueError("Unsupported risk tolerance.")
    position_fraction, sector_fraction = CAPS[risk_tolerance]
    position_cap = funds * position_fraction
    sector_cap = funds * sector_fraction

    valid = []
    excluded = []
    seen = set()
    for item in candidates:
        symbol = str(item.get("symbol") or "").strip().upper()
        if not symbol or symbol in seen:
            excluded.append({"symbol": symbol or "UNKNOWN",
                             "reason": "Missing or duplicate stock symbol."})
            continue
        seen.add(symbol)
        ccy = item.get("currency")
        if not isinstance(ccy, str) or ccy.strip().upper() != currency:
            excluded.append({"symbol": symbol,
                             "reason": "Missing or mismatched trading currency."})
            continue
        price = _amount(item.get("latest_price"))
        if price is None or price <= 0:
            excluded.append({"symbol": symbol, "reason": "Invalid stored share price."})
            continue
        # Names without a verified sector share a conservative unknown-sector
        # exposure bucket rather than being treated as unrelated sectors.
        sector = str(item.get("sector") or "").strip() or "Unknown"
        valid.append({
            "symbol": symbol,
            "company_name": item.get("company_name"),
            "exchange": item.get("exchange"),
            "sector": sector,
            "currency": currency,
            "price": price,
            "rank": item.get("rank"),
            "score": item.get("score"),
        })

    units = defaultdict(int)
    spent_by_sector = defaultdict(lambda: Decimal("0"))
    spent = Decimal("0")
    portfolio = []

    # First pass: favor breadth while respecting ranked input priority.
    for item in valid:
        if len(portfolio) >= max_allocations:
            break
        price = item["price"]
        sector = item["sector"]
        if (
            price > funds - spent
            or price > position_cap
            or price > sector_cap - spent_by_sector[sector]
        ):
            excluded.append({
                "symbol": item["symbol"],
                "reason": "Whole-share price exceeds available cash or concentration cap.",
            })
            continue
        portfolio.append(item)
        units[item["symbol"]] = 1
        spent += price
        spent_by_sector[sector] += price

    # Second pass: add ranked shares, but never breach either hard cap.
    for item in portfolio:
        price = item["price"]
        sector = item["sector"]
        position_spent = price * units[item["symbol"]]
        affordable = min(
            funds - spent,
            position_cap - position_spent,
            sector_cap - spent_by_sector[sector],
        )
        if affordable < price:
            continue
        more = int((affordable / price).to_integral_value(rounding=ROUND_FLOOR))
        if more <= 0:
            continue
        units[item["symbol"]] += more
        charge = price * more
        spent += charge
        spent_by_sector[sector] += charge

    remaining = funds - spent
    if spent < 0 or remaining < 0 or spent + remaining != funds:
        raise ArithmeticError("Illustrative allocation failed conservation of funds.")
    allocations = []
    for item in portfolio:
        cost = item["price"] * units[item["symbol"]]
        if cost > position_cap or spent_by_sector[item["sector"]] > sector_cap:
            raise ArithmeticError("Illustrative allocation breached concentration cap.")
        allocations.append({
            "symbol": item["symbol"],
            "company_name": item["company_name"],
            "exchange": item["exchange"],
            "sector": item["sector"],
            "currency": currency,
            "latest_price": str(item["price"]),
            "shares": units[item["symbol"]],
            "estimated_cost": str(cost),
            "share_of_budget_percent": float(
                (cost / funds * Decimal("100")).quantize(Decimal("0.01"))
            ),
            "rank": item["rank"],
            "score": item["score"],
        })

    return {
        "method": "diversified_caps_v1",
        "currency": currency,
        "budget": str(funds),
        "invested": str(spent) if allocations else "0.00",
        "remaining_cash": str(remaining),
        "allocations": allocations,
        "excluded": excluded,
        "position_cap_percent": int(position_fraction * 100),
        "sector_cap_percent": int(sector_fraction * 100),
        "sector_exposure": {
            sector: str(amount)
            for sector, amount in sorted(spent_by_sector.items())
            if amount > 0
        },
        "fractional_shares_used": False,
        "disclaimer": (
            "Illustrative, whole-share, ranking-aware paper allocation. "
            "Fixed position/sector caps are policy examples, not optimized investment "
            "weights; uninvested cash is intentional when caps or whole-share prices bind. "
            "No execution, tax, liquidity, transaction costs, FX or personalized suitability."
        ),
    }
