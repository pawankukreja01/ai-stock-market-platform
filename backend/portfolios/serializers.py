from decimal import Decimal

from rest_framework import serializers

from market_data.models import HistoricalPrice
from stocks.models import Stock
from .models import Portfolio, PortfolioHolding


def normalize_currency(value):
    """Return a usable ISO-style currency code or UNKNOWN."""
    if isinstance(value, str):
        code = value.strip().upper()
        if len(code) == 3 and code.isalpha():
            return code
    return "UNKNOWN"


def get_stock_currency(stock, price_currency=None):
    """Prefer the currency attached to stored prices, then stock metadata."""
    price_code = normalize_currency(price_currency)
    if price_code != "UNKNOWN":
        return price_code
    return normalize_currency(getattr(stock, "currency", ""))


def get_portfolio_valuation(portfolio, context):
    """Calculate valuations without adding different currencies together."""
    cache = context.setdefault("_portfolio_valuation_cache", {})
    if portfolio.pk in cache:
        return cache[portfolio.pk]

    holdings = list(portfolio.holdings.select_related("stock").all())
    holding_values = {}
    groups = {}
    latest_dates = []

    for holding in holdings:
        quantity = holding.quantity
        cost_basis = quantity * holding.purchase_price
        latest_price = (
            HistoricalPrice.objects
            .filter(stock_id=holding.stock_id, close_price__gt=0)
            .order_by("-date")
            .values("close_price", "date", "storage_currency")
            .first()
        )

        currency = get_stock_currency(
            holding.stock,
            latest_price.get("storage_currency") if latest_price else None,
        )
        group = groups.setdefault(currency, {
            "currency": currency,
            "holdings_count": 0,
            "priced_holdings": 0,
            "unpriced_holdings": 0,
            "total_cost_basis": Decimal("0"),
            "priced_cost_basis": Decimal("0"),
            "market_value": Decimal("0"),
            "unrealized_profit_loss": Decimal("0"),
            "latest_dates": [],
        })
        group["holdings_count"] += 1
        group["total_cost_basis"] += cost_basis

        if latest_price is None:
            current_price = None
            current_value = None
            profit_loss = None
            return_pct = None
            price_date = None
            group["unpriced_holdings"] += 1
        else:
            current_price = Decimal(str(latest_price["close_price"]))
            current_value = quantity * current_price
            profit_loss = current_value - cost_basis
            return_pct = (
                profit_loss / cost_basis * Decimal("100")
                if cost_basis > 0 else None
            )
            price_date = latest_price["date"]
            group["priced_holdings"] += 1
            group["priced_cost_basis"] += cost_basis
            group["market_value"] += current_value
            group["unrealized_profit_loss"] += profit_loss
            group["latest_dates"].append(price_date)
            latest_dates.append(price_date)

        holding_values[holding.pk] = {
            "current_price": current_price,
            "current_price_date": price_date,
            "current_value": current_value,
            "cost_basis": cost_basis,
            "unrealized_profit_loss": profit_loss,
            "unrealized_return_pct": return_pct,
            "weight_pct": None,
            "currency": currency,
        }

    currency_breakdown = []
    for currency in sorted(groups):
        group = groups[currency]
        market_value = group["market_value"]
        priced_cost_basis = group["priced_cost_basis"]
        group_return = (
            group["unrealized_profit_loss"] / priced_cost_basis * Decimal("100")
            if priced_cost_basis > 0 else None
        )

        # Holding weights are meaningful only within the same currency group.
        if market_value > 0:
            for holding in holdings:
                values = holding_values[holding.pk]
                if values["currency"] == currency and values["current_value"] is not None:
                    values["weight_pct"] = (
                        values["current_value"] / market_value * Decimal("100")
                    )

        currency_breakdown.append({
            "currency": currency,
            "holdings_count": group["holdings_count"],
            "priced_holdings": group["priced_holdings"],
            "unpriced_holdings": group["unpriced_holdings"],
            "total_cost_basis": float(group["total_cost_basis"]),
            "priced_cost_basis": float(priced_cost_basis),
            "market_value": float(market_value),
            "unrealized_profit_loss": float(group["unrealized_profit_loss"]),
            "unrealized_return_pct": float(group_return) if group_return is not None else None,
            "data_as_of": max(group["latest_dates"]).isoformat() if group["latest_dates"] else None,
        })

    mixed_currencies = len(currency_breakdown) > 1
    only_group = currency_breakdown[0] if len(currency_breakdown) == 1 else None

    summary = {
        "holdings_count": len(holding_values),
        "priced_holdings": sum(item["priced_holdings"] for item in currency_breakdown),
        "unpriced_holdings": sum(item["unpriced_holdings"] for item in currency_breakdown),
        "currency_count": len(currency_breakdown),
        "currencies": [item["currency"] for item in currency_breakdown],
        "mixed_currencies": mixed_currencies,
        "currency": only_group["currency"] if only_group else None,
        # Legacy aggregate fields remain populated for single-currency portfolios.
        # They are deliberately null for mixed-currency portfolios: adding GBP and
        # USD amounts without an FX rate would produce a misleading total.
        "total_cost_basis": only_group["total_cost_basis"] if only_group else None,
        "priced_cost_basis": only_group["priced_cost_basis"] if only_group else None,
        "market_value": only_group["market_value"] if only_group else None,
        "unrealized_profit_loss": only_group["unrealized_profit_loss"] if only_group else None,
        "unrealized_return_pct": only_group["unrealized_return_pct"] if only_group else None,
        "data_as_of": max(latest_dates).isoformat() if latest_dates else None,
        "currency_breakdown": currency_breakdown,
        "valuation_note": (
            "Values are grouped by holding currency. No foreign-exchange conversion is applied."
            if mixed_currencies else
            "Values use the holding currency and latest stored closing prices."
        ),
    }

    result = {"holdings": holding_values, "summary": summary}
    cache[portfolio.pk] = result
    return result


class PortfolioHoldingSerializer(serializers.ModelSerializer):
    stock_symbol = serializers.SlugRelatedField(
        source="stock",
        slug_field="symbol",
        queryset=Stock.objects.filter(is_active=True),
    )
    company_name = serializers.CharField(source="stock.company_name", read_only=True)
    exchange = serializers.CharField(source="stock.exchange", read_only=True)
    sector = serializers.CharField(source="stock.sector", read_only=True)
    industry = serializers.CharField(source="stock.industry", read_only=True)
    current_price = serializers.SerializerMethodField()
    current_price_date = serializers.SerializerMethodField()
    current_value = serializers.SerializerMethodField()
    cost_basis = serializers.SerializerMethodField()
    unrealized_profit_loss = serializers.SerializerMethodField()
    unrealized_return_pct = serializers.SerializerMethodField()
    weight_pct = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()

    class Meta:
        model = PortfolioHolding
        fields = [
            "id", "stock_symbol", "company_name", "exchange", "sector", "industry",
            "currency", "quantity", "purchase_price", "purchase_date",
            "current_price", "current_price_date", "current_value", "cost_basis",
            "unrealized_profit_loss", "unrealized_return_pct", "weight_pct",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "company_name", "exchange", "sector", "industry", "currency",
            "current_price", "current_price_date", "current_value", "cost_basis",
            "unrealized_profit_loss", "unrealized_return_pct", "weight_pct",
            "created_at", "updated_at",
        ]
        validators = []

    def validate(self, attrs):
        portfolio = self.context.get("portfolio")
        stock = attrs.get("stock")
        if stock is None and self.instance is not None:
            stock = self.instance.stock

        if portfolio is not None and stock is not None:
            existing = PortfolioHolding.objects.filter(portfolio=portfolio, stock=stock)
            if self.instance is not None:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError({
                    "stock_symbol": (
                        "This stock already exists in this portfolio. "
                        "Update its existing holding instead."
                    )
                })
        return attrs

    def _values(self, obj):
        valuation = get_portfolio_valuation(obj.portfolio, self.context)
        return valuation["holdings"].get(obj.pk, {})

    def get_current_price(self, obj):
        return self._number(self._values(obj).get("current_price"))

    def get_current_price_date(self, obj):
        return self._values(obj).get("current_price_date")

    def get_current_value(self, obj):
        return self._number(self._values(obj).get("current_value"))

    def get_cost_basis(self, obj):
        return self._number(self._values(obj).get("cost_basis"))

    def get_unrealized_profit_loss(self, obj):
        return self._number(self._values(obj).get("unrealized_profit_loss"))

    def get_unrealized_return_pct(self, obj):
        return self._number(self._values(obj).get("unrealized_return_pct"))

    def get_weight_pct(self, obj):
        return self._number(self._values(obj).get("weight_pct"))

    def get_currency(self, obj):
        return self._values(obj).get("currency") or get_stock_currency(obj.stock)

    @staticmethod
    def _number(value):
        return float(value) if value is not None else None


class PortfolioSerializer(serializers.ModelSerializer):
    holdings = PortfolioHoldingSerializer(many=True, read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = [
            "id", "name", "description", "created_at", "updated_at",
            "holdings", "summary",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "holdings", "summary"]

    def get_summary(self, obj):
        return get_portfolio_valuation(obj, self.context)["summary"]
