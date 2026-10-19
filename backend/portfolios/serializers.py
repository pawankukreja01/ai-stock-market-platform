from decimal import Decimal

from rest_framework import serializers

from market_data.models import HistoricalPrice
from stocks.models import Stock
from .models import Portfolio, PortfolioHolding


def get_portfolio_valuation(portfolio, context):
    """
    Calculate the latest stored-price valuation for a portfolio.

    Results are cached in serializer context to avoid recalculating
    the same portfolio valuation for every serialized field.
    """
    cache = context.setdefault("_portfolio_valuation_cache", {})

    if portfolio.pk in cache:
        return cache[portfolio.pk]

    holdings = portfolio.holdings.select_related("stock").all()

    holding_values = {}
    total_market_value = Decimal("0")
    total_cost_basis = Decimal("0")
    priced_cost_basis = Decimal("0")
    total_profit_loss = Decimal("0")
    priced_holdings = 0
    unpriced_holdings = 0
    latest_dates = []

    for holding in holdings:
        quantity = holding.quantity
        cost_basis = quantity * holding.purchase_price
        total_cost_basis += cost_basis

        latest_price = (
            HistoricalPrice.objects
            .filter(stock_id=holding.stock_id)
            .order_by("-date")
            .values("close_price", "date")
            .first()
        )

        if latest_price is None:
            current_price = None
            current_value = None
            profit_loss = None
            return_pct = None
            price_date = None
            weight_pct = None
            unpriced_holdings += 1
        else:
            current_price = Decimal(str(latest_price["close_price"]))
            current_value = quantity * current_price
            profit_loss = current_value - cost_basis
            return_pct = (
                profit_loss / cost_basis * Decimal("100")
                if cost_basis > 0
                else None
            )
            price_date = latest_price["date"]

            total_market_value += current_value
            priced_cost_basis += cost_basis
            total_profit_loss += profit_loss
            priced_holdings += 1
            latest_dates.append(price_date)

            weight_pct = None

        holding_values[holding.pk] = {
            "current_price": current_price,
            "current_price_date": price_date,
            "current_value": current_value,
            "cost_basis": cost_basis,
            "unrealized_profit_loss": profit_loss,
            "unrealized_return_pct": return_pct,
            "weight_pct": weight_pct,
        }

    # Portfolio weights require the total market value.
    for holding in holdings:
        values = holding_values[holding.pk]

        if (
            values["current_value"] is not None
            and total_market_value > 0
        ):
            values["weight_pct"] = (
                values["current_value"]
                / total_market_value
                * Decimal("100")
            )

    unrealized_return_pct = (
        total_profit_loss / priced_cost_basis * Decimal("100")
        if priced_cost_basis > 0
        else None
    )

    summary = {
        "holdings_count": len(holding_values),
        "priced_holdings": priced_holdings,
        "unpriced_holdings": unpriced_holdings,
        "total_cost_basis": float(total_cost_basis),
        "priced_cost_basis": float(priced_cost_basis),
        "market_value": float(total_market_value),
        "unrealized_profit_loss": float(total_profit_loss),
        "unrealized_return_pct": (
            float(unrealized_return_pct)
            if unrealized_return_pct is not None
            else None
        ),
        "data_as_of": (
            max(latest_dates).isoformat()
            if latest_dates
            else None
        ),
    }

    result = {
        "holdings": holding_values,
        "summary": summary,
    }

    cache[portfolio.pk] = result
    return result


class PortfolioHoldingSerializer(serializers.ModelSerializer):
    stock_symbol = serializers.SlugRelatedField(
        source="stock",
        slug_field="symbol",
        queryset=Stock.objects.filter(is_active=True),
    )
    company_name = serializers.CharField(
        source="stock.company_name",
        read_only=True,
    )
    current_price = serializers.SerializerMethodField()
    current_price_date = serializers.SerializerMethodField()
    current_value = serializers.SerializerMethodField()
    cost_basis = serializers.SerializerMethodField()
    unrealized_profit_loss = serializers.SerializerMethodField()
    unrealized_return_pct = serializers.SerializerMethodField()
    weight_pct = serializers.SerializerMethodField()

    class Meta:
        model = PortfolioHolding
        fields = [
            "id",
            "stock_symbol",
            "company_name",
            "quantity",
            "purchase_price",
            "purchase_date",
            "current_price",
            "current_price_date",
            "cost_basis",
            "current_value",
            "unrealized_profit_loss",
            "unrealized_return_pct",
            "weight_pct",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "company_name",
            "current_price",
            "current_price_date",
            "cost_basis",
            "current_value",
            "unrealized_profit_loss",
            "unrealized_return_pct",
            "weight_pct",
            "created_at",
            "updated_at",
        ]
        validators = []

    def validate(self, attrs):
        portfolio = self.context.get("portfolio")
        stock = attrs.get("stock")

        if stock is None and self.instance is not None:
            stock = self.instance.stock

        if portfolio is not None and stock is not None:
            existing = PortfolioHolding.objects.filter(
                portfolio=portfolio,
                stock=stock,
            )

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
        valuation = get_portfolio_valuation(
            obj.portfolio,
            self.context,
        )
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
        return self._number(
            self._values(obj).get("unrealized_profit_loss")
        )

    def get_unrealized_return_pct(self, obj):
        return self._number(
            self._values(obj).get("unrealized_return_pct")
        )

    def get_weight_pct(self, obj):
        return self._number(self._values(obj).get("weight_pct"))

    @staticmethod
    def _number(value):
        return float(value) if value is not None else None


class PortfolioSerializer(serializers.ModelSerializer):
    holdings = PortfolioHoldingSerializer(many=True, read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
            "holdings",
            "summary",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "holdings",
            "summary",
        ]

    def get_summary(self, obj):
        return get_portfolio_valuation(obj, self.context)["summary"]