from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from market_data.models import HistoricalPrice
from stocks.models import Stock
from portfolios.models import Portfolio, PortfolioHolding


class PortfolioAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="portfolio_owner", password="test-only-password"
        )
        self.client.force_authenticate(user=self.user)
        self.stock = Stock.objects.create(
            symbol="AAPL",
            company_name="Apple Inc.",
            exchange="NASDAQ",
            currency="USD",
            sector="Technology",
            industry="Consumer Electronics",
            is_active=True,
        )
        self.portfolio = Portfolio.objects.create(
            owner=self.user,
            name="Test Portfolio",
            description="Portfolio API test",
        )
        self.base_date = date(2026, 9, 1)
        self.create_price_history(self.stock)

    def create_price_history(self, stock, start=Decimal("100.0000")):
        rows = []
        for index in range(35):
            price = start + Decimal(index)
            rows.append(HistoricalPrice(
                stock=stock,
                date=self.base_date + timedelta(days=index),
                open_price=price,
                high_price=price + Decimal("1.0000"),
                low_price=price - Decimal("1.0000"),
                close_price=price,
                adjusted_close=price,
                volume=1000000,
                storage_currency=stock.currency,
            ))
        HistoricalPrice.objects.bulk_create(rows)

    def add_holding(self, quantity="3", purchase_price="100.00"):
        return self.client.post(
            f"/api/portfolios/{self.portfolio.id}/holdings/",
            {
                "stock_symbol": "AAPL",
                "quantity": quantity,
                "purchase_price": purchase_price,
                "purchase_date": "2026-09-01",
            },
            format="json",
        )

    def test_create_portfolio(self):
        response = self.client.post(
            "/api/portfolios/",
            {"name": "Long-term Portfolio", "description": "Long-term investment test"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Long-term Portfolio")
        self.assertEqual(response.data["summary"]["holdings_count"], 0)

    def test_add_holding_and_calculate_valuation(self):
        response = self.add_holding(quantity="3", purchase_price="100.00")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["stock_symbol"], "AAPL")
        self.assertEqual(response.data["currency"], "USD")
        self.assertAlmostEqual(response.data["current_price"], 134.00)
        self.assertAlmostEqual(response.data["cost_basis"], 300.00)
        self.assertAlmostEqual(response.data["current_value"], 402.00)
        self.assertAlmostEqual(response.data["unrealized_profit_loss"], 102.00)
        self.assertAlmostEqual(response.data["unrealized_return_pct"], 34.00)
        self.assertAlmostEqual(response.data["weight_pct"], 100.00)

    def test_valuation_ignores_non_positive_latest_close(self):
        HistoricalPrice.objects.create(
            stock=self.stock,
            date=date(2026, 10, 6),
            open_price=Decimal("0.0000"),
            high_price=Decimal("0.0000"),
            low_price=Decimal("0.0000"),
            close_price=Decimal("0.0000"),
            adjusted_close=Decimal("0.0000"),
            volume=0,
            storage_currency="USD",
            is_ohlc_valid=False,
            is_volume_valid=True,
            quality_flags={"ohlc": "non_positive_close"},
        )
        response = self.add_holding(quantity="3", purchase_price="100.00")
        self.assertEqual(response.status_code, 201)
        self.assertAlmostEqual(response.data["current_price"], 134.00)
        self.assertEqual(response.data["current_price_date"], date(2026, 10, 5))

    def test_portfolio_risk_preserves_adjusted_close_gap(self):
        HistoricalPrice.objects.filter(
            stock=self.stock,
            date=date(2026, 9, 18),
        ).update(adjusted_close=Decimal("0.0000"))
        self.add_holding(quantity="3", purchase_price="100.00")
        response = self.client.get(f"/api/portfolios/{self.portfolio.id}/analysis/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["risk"]["available"])
        self.assertEqual(response.data["risk"]["observations"], 32)

    def test_portfolio_detail_includes_currency_summary(self):
        self.add_holding(quantity="3", purchase_price="100.00")
        response = self.client.get(f"/api/portfolios/{self.portfolio.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["holdings"]), 1)
        summary = response.data["summary"]
        self.assertEqual(summary["holdings_count"], 1)
        self.assertEqual(summary["priced_holdings"], 1)
        self.assertEqual(summary["unpriced_holdings"], 0)
        self.assertEqual(summary["currency"], "USD")
        self.assertFalse(summary["mixed_currencies"])
        self.assertAlmostEqual(summary["total_cost_basis"], 300.00)
        self.assertAlmostEqual(summary["market_value"], 402.00)
        self.assertAlmostEqual(summary["unrealized_profit_loss"], 102.00)
        self.assertEqual(len(summary["currency_breakdown"]), 1)

    def test_mixed_currency_portfolio_never_adds_currency_amounts(self):
        self.add_holding(quantity="3", purchase_price="100.00")
        vod = Stock.objects.create(
            symbol="VOD.L",
            company_name="Vodafone Group Plc",
            exchange="LSE",
            currency="GBP",
            sector="Communication Services",
            industry="Telecom Services",
            is_active=True,
        )
        self.create_price_history(vod)
        PortfolioHolding.objects.create(
            portfolio=self.portfolio,
            stock=vod,
            quantity=Decimal("2"),
            purchase_price=Decimal("100.00"),
            purchase_date=self.base_date,
        )

        detail = self.client.get(f"/api/portfolios/{self.portfolio.id}/")
        self.assertEqual(detail.status_code, 200)
        summary = detail.data["summary"]
        self.assertTrue(summary["mixed_currencies"])
        self.assertEqual(summary["currencies"], ["GBP", "USD"])
        self.assertIsNone(summary["market_value"])
        self.assertIsNone(summary["total_cost_basis"])
        self.assertEqual(len(summary["currency_breakdown"]), 2)
        by_currency = {item["currency"]: item for item in summary["currency_breakdown"]}
        self.assertAlmostEqual(by_currency["USD"]["market_value"], 402.00)
        self.assertAlmostEqual(by_currency["GBP"]["market_value"], 268.00)

    def test_mixed_currency_risk_is_reported_separately(self):
        self.add_holding()
        vod = Stock.objects.create(
            symbol="VOD.L",
            company_name="Vodafone Group Plc",
            exchange="LSE",
            currency="GBP",
            sector="Communication Services",
            industry="Telecom Services",
            is_active=True,
        )
        self.create_price_history(vod)
        PortfolioHolding.objects.create(
            portfolio=self.portfolio,
            stock=vod,
            quantity=Decimal("2"),
            purchase_price=Decimal("100.00"),
            purchase_date=self.base_date,
        )

        response = self.client.get(f"/api/portfolios/{self.portfolio.id}/analysis/")
        self.assertEqual(response.status_code, 200)
        risk = response.data["risk"]
        self.assertFalse(risk["available"])
        self.assertEqual([item["currency"] for item in risk["by_currency"]], ["GBP", "USD"])
        self.assertTrue(all(item["available"] for item in risk["by_currency"]))

    def test_duplicate_stock_cannot_be_added_twice(self):
        first_response = self.add_holding()
        self.assertEqual(first_response.status_code, 201)
        second_response = self.add_holding(quantity="5", purchase_price="110.00")
        self.assertEqual(second_response.status_code, 400)
        self.assertEqual(PortfolioHolding.objects.filter(portfolio=self.portfolio, stock=self.stock).count(), 1)

    def test_holding_can_be_updated(self):
        create_response = self.add_holding()
        self.assertEqual(create_response.status_code, 201)
        holding_id = create_response.data["id"]
        update_response = self.client.patch(
            f"/api/portfolios/{self.portfolio.id}/holdings/{holding_id}/",
            {"quantity": "5", "purchase_price": "110.00"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(Decimal(update_response.data["quantity"]), Decimal("5"))
        self.assertEqual(Decimal(update_response.data["purchase_price"]), Decimal("110.00"))

    def test_holding_can_be_removed(self):
        create_response = self.add_holding()
        holding_id = create_response.data["id"]
        delete_response = self.client.delete(
            f"/api/portfolios/{self.portfolio.id}/holdings/{holding_id}/"
        )
        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(PortfolioHolding.objects.filter(pk=holding_id).exists())

    def test_portfolio_risk_analysis_returns_metrics(self):
        self.add_holding(quantity="3", purchase_price="100.00")
        response = self.client.get(f"/api/portfolios/{self.portfolio.id}/analysis/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["risk"]["available"])
        risk = response.data["risk"]
        self.assertIn("annualized_volatility_pct", risk)
        self.assertIn("max_drawdown_pct", risk)
        self.assertIn("period_return_pct", risk)
        self.assertIn("annualized_return_pct", risk)
        self.assertEqual(risk["included_symbols"], ["AAPL"])
        self.assertGreater(risk["observations"], 20)

    def test_empty_portfolio_reports_risk_unavailable(self):
        response = self.client.get(f"/api/portfolios/{self.portfolio.id}/analysis/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["risk"]["available"])

    def test_anonymous_portfolio_api_rejected(self):
        anonymous = APIClient()
        self.assertIn(anonymous.get("/api/portfolios/").status_code, (401, 403))
        self.assertIn(anonymous.get(f"/api/portfolios/{self.portfolio.pk}/").status_code, (401, 403))

    def test_cross_user_portfolio_and_holding_access_denied(self):
        other = get_user_model().objects.create_user(
            username="other_portfolio_user", password="test-only-password"
        )
        foreign = Portfolio.objects.create(name="Private", owner=other)
        holding = PortfolioHolding.objects.create(
            portfolio=foreign, stock=self.stock,
            quantity=Decimal("1"), purchase_price=Decimal("100.00")
        )
        response = self.client.get("/api/portfolios/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(foreign.pk, [p["id"] for p in response.data])
        self.assertEqual(self.client.get(f"/api/portfolios/{foreign.pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/portfolios/{foreign.pk}/analysis/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/portfolios/{foreign.pk}/holdings/").status_code, 404)
        self.assertEqual(self.client.patch(
            f"/api/portfolios/{foreign.pk}/", {"name": "Stolen"}, format="json"
        ).status_code, 404)
        self.assertEqual(self.client.delete(f"/api/portfolios/{foreign.pk}/").status_code, 404)
        self.assertEqual(self.client.patch(
            f"/api/portfolios/{foreign.pk}/holdings/{holding.pk}/",
            {"quantity": "200"}, format="json"
        ).status_code, 404)
        self.assertTrue(Portfolio.objects.filter(pk=foreign.pk, owner=other).exists())
        self.assertEqual(PortfolioHolding.objects.get(pk=holding.pk).quantity, Decimal("1"))

    def test_new_portfolio_ignores_spoofed_owner(self):
        other = get_user_model().objects.create_user(
            username="other_portfolio_target", password="test-only-password"
        )
        r = self.client.post(
            "/api/portfolios/", {"name": "Mine", "owner": other.pk}, format="json"
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Portfolio.objects.get(pk=r.data["id"]).owner, self.user)
        self.assertNotIn("owner", r.data)

    def test_legacy_portfolio_preserved_and_hidden(self):
        legacy = Portfolio.objects.create(name="Orphaned legacy portfolio")
        self.assertEqual(self.client.get(f"/api/portfolios/{legacy.pk}/").status_code, 404)
        self.assertTrue(Portfolio.objects.filter(pk=legacy.pk, owner__isnull=True).exists())
