
import re
from decimal import Decimal, InvalidOperation, ROUND_FLOOR


def allocate_whole_shares(
    candidates,
    *,
    budget,
    currency,
    max_allocations=10,
):
    """
    Allocate a budget using a ranking-first, whole-share strategy.

    Candidates must already be ordered from highest to lowest rank.
    The allocator buys as many whole shares as possible for each candidate
    before proceeding to the next candidate.

    Currency conversion and fractional shares are not supported.
    """

    # Validate budget.
    try:
        budget = Decimal(str(budget))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Budget must be a valid decimal amount.")

    if not budget.is_finite() or budget <= 0:
        raise ValueError("Budget must be greater than zero.")

    # Validate currency.
    currency = str(currency).strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("Currency must be a three-letter code.")

    # Validate allocation limit.
    if (
        isinstance(max_allocations, bool)
        or not isinstance(max_allocations, int)
        or not 1 <= max_allocations <= 100
    ):
        raise ValueError("max_allocations must be between 1 and 100.")

    eligible = []
    excluded = []

    # Validate candidates while preserving their input ranking order.
    for candidate in candidates:
        symbol = candidate.get("symbol", "UNKNOWN")
        candidate_currency = candidate.get("currency")
        raw_price = candidate.get("latest_price")

        # Require an explicitly matching currency.
        if (
            not isinstance(candidate_currency, str)
            or candidate_currency.strip().upper() != currency
        ):
            excluded.append({
                "symbol": symbol,
                "reason": "Unknown or mismatched trading currency.",
            })
            continue

        # Validate the share price.
        try:
            price = Decimal(str(raw_price))
        except (InvalidOperation, TypeError, ValueError):
            price = None

        if price is None or not price.is_finite() or price <= 0:
            excluded.append({
                "symbol": symbol,
                "reason": "Missing or invalid latest price.",
            })
            continue

        eligible.append({
            "symbol": symbol,
            "company_name": candidate.get("company_name"),
            "exchange": candidate.get("exchange"),
            "currency": currency,
            "price": price,
            "rank": candidate.get("rank"),
            "score": candidate.get("score"),
        })

    allocations = []
    allocated_symbols = set()
    invested = Decimal("0")

    # Ranking-first: allocate as many whole shares as possible to each
    # candidate before considering the next candidate.
    for candidate in eligible:
        if len(allocations) >= max_allocations:
            break

        remaining = budget - invested
        if remaining <= 0:
            break

        price = candidate["price"]
        shares = int(
            (remaining / price).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )

        # Skip stocks that are not affordable with the remaining budget.
        if shares <= 0:
            continue

        symbol = candidate["symbol"]

        # Avoid duplicate allocation entries for the same symbol.
        if symbol in allocated_symbols:
            continue

        cost = price * shares

        # Defensive budget check.
        if cost > remaining:
            continue

        allocations.append({
            "symbol": symbol,
            "company_name": candidate["company_name"],
            "exchange": candidate["exchange"],
            "currency": currency,
            "latest_price": str(price),
            "shares": shares,
            "estimated_cost": str(cost),
            "rank": candidate["rank"],
            "score": candidate["score"],
        })

        allocated_symbols.add(symbol)
        invested += cost

    remaining_cash = budget - invested

    # Enforce accounting invariants.
    if invested > budget or remaining_cash < 0:
        raise ArithmeticError("Allocation exceeded the available budget.")

    if invested + remaining_cash != budget:
        raise ArithmeticError("Allocation totals do not match the budget.")

    # Preserve compatibility with existing tests:
    # - Empty allocations expect invested == "0.00".
    # - Non-empty allocations preserve Decimal's original string scale.
    invested_output = (
        "0.00" if not allocations else str(invested)
    )

    return {
        "currency": currency,
        "budget": str(budget),
        "invested": invested_output,
        "remaining_cash": str(remaining_cash),
        "allocations": allocations,
        "excluded": excluded,
        "fractional_shares_used": False,
        "disclaimer": (
            "Illustrative ranking-first allocation based on stored prices "
            "and whole shares. Prices can change, and this does not verify "
            "execution, fees, taxes, settlement, or broker-specific "
            "trading restrictions."
        ),
    }
