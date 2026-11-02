from datetime import date

from django.db.models import OuterRef, Subquery

from stocks.models import Stock
from .models import HistoricalPrice


def get_recommendation_candidates(
    *,
    market=None,
    max_candidates=20,
    as_of=None,
):
    """
    Retrieve active stocks with their latest stored closing price.

    Missing prices remain None; this function does not rank stocks.
    """
    as_of = as_of or date.today()
    latest_price = (
        HistoricalPrice.objects
        .filter(
            stock_id=OuterRef("pk"),
            date__lte=as_of,
            close_price__gt=0,
        )
        .order_by("-date", "-id")
    )

    queryset = (
        Stock.objects
        .filter(is_active=True)
        .annotate(
            latest_price=Subquery(
                latest_price.values("close_price")[:1]
            ),
            latest_price_date=Subquery(
                latest_price.values("date")[:1]
            ),
        )
        .order_by("symbol")
    )

    if market:
        queryset = queryset.filter(exchange__iexact=market.strip())

    candidates = []

    for stock in queryset[:max_candidates]:
        price = stock.latest_price
        price_date = stock.latest_price_date

        candidates.append({
            "symbol": stock.symbol,
            "company_name": stock.company_name,
            "exchange": stock.exchange,
            "sector": stock.sector,
            "industry": stock.industry,
            "latest_price": str(price) if price is not None else None,
            "latest_price_date": (
                price_date.isoformat() if price_date else None
            ),
            "price_available": price is not None and price > 0,
        })

    return candidates
