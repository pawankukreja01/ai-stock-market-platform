from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from market_data.models import HistoricalPrice
from stocks.models import Stock


class InvestmentSimulatorAPITests(TestCase):
    """Test historical investment simulations and validation."""

    def setUp(self):
        self.client = APIClient()

        self.stock = Stock.objects.create(
            symbol="AAPL",
            company_name="Apple Inc.",
            exchange="NASDAQ",
            sector="Technology",
            industry="Consumer Electronics",
            is_active=True,
        )

        self.start_date = date(2025, 1, 1)
        records = []

        # Create deterministic synthetic prices for 100 days.
        # These values are for testing, not real market data.
        for index in range(100):
            trading_date = self.start_date + timedelta(days=index)
            price = Decimal("100.0000") + (
                Decimal(index) * Decimal("0.5000")
            )

            records.append(
                HistoricalPrice(
                    stock=self.stock,
                    date=trading_date,
                    open_price=price,
                    high_price=price + Decimal("1.0000"),
                    low_price=price - Decimal("1.0000"),
                    close_price=price,
                    adjusted_close=price,
                    volume=1000000,
                )
            )

        HistoricalPrice.objects.bulk_create(records)

    def simulation_params(self, **overrides):
        params = {
            "symbol": "AAPL",
            "start_date": "2025-01-01",
            "end_date": "2025-04-10",
            "initial_investment": "10000",
            "monthly_contribution": "200",
        }
        params.update(overrides)
        return params

    def test_successful_lump_sum_and_monthly_simulation(self):
        response = self.client.get(
            "/api/investment-simulator/",
            self.simulation_params(),
        )

        self.assertEqual(response.status_code, 200)

        data = response.data

        self.assertEqual(data["symbol"], "AAPL")
        self.assertEqual(
            data["actual_period"]["price_observations"],
            100,
        )

        summary = data["summary"]

        self.assertAlmostEqual(
            summary["initial_investment"],
            10000.0,
        )
        self.assertAlmostEqual(
            summary["monthly_contribution"],
            200.0,
        )

        # The selected period contains February, March and April
        # after the initial January investment month.
        self.assertEqual(summary["contribution_count"], 3)
        self.assertAlmostEqual(
            summary["additional_contributions"],
            600.0,
        )
        self.assertAlmostEqual(
            summary["total_invested"],
            10600.0,
        )

        self.assertGreater(summary["ending_value"], 0)
        self.assertGreater(summary["profit_loss"], 0)
        self.assertGreater(summary["total_return_pct"], 0)

        self.assertEqual(len(data["curve"]), 100)

        self.assertEqual(
            data["curve"][0]["date"],
            "2025-01-01",
        )
        self.assertEqual(
            data["curve"][-1]["date"],
            "2025-04-10",
        )

    def test_lump_sum_simulation_without_monthly_contributions(self):
        response = self.client.get(
            "/api/investment-simulator/",
            self.simulation_params(monthly_contribution="0"),
        )

        self.assertEqual(response.status_code, 200)

        summary = response.data["summary"]

        self.assertEqual(summary["contribution_count"], 0)
        self.assertAlmostEqual(
            summary["additional_contributions"],
            0.0,
        )
        self.assertAlmostEqual(
            summary["total_invested"],
            10000.0,
        )

        self.assertGreater(summary["ending_value"], 10000.0)

    def test_reject_missing_symbol(self):
        params = self.simulation_params()
        params.pop("symbol")

        response = self.client.get(
            "/api/investment-simulator/",
            params,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_reject_invalid_date_format(self):
        response = self.client.get(
            "/api/investment-simulator/",
            self.simulation_params(start_date="not-a-date"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_reject_end_date_before_start_date(self):
        response = self.client.get(
            "/api/investment-simulator/",
            self.simulation_params(
                start_date="2025-03-01",
                end_date="2025-02-01",
            ),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_reject_zero_initial_investment(self):
        response = self.client.get(
            "/api/investment-simulator/",
            self.simulation_params(initial_investment="0"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_reject_negative_monthly_contribution(self):
        response = self.client.get(
            "/api/investment-simulator/",
            self.simulation_params(monthly_contribution="-100"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_reject_unknown_stock(self):
        response = self.client.get(
            "/api/investment-simulator/",
            self.simulation_params(symbol="UNKNOWN"),
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.data)

    def test_reject_insufficient_historical_prices(self):
        Stock.objects.create(
            symbol="MSFT",
            company_name="Microsoft Corporation",
            exchange="NASDAQ",
            sector="Technology",
            industry="Software",
            is_active=True,
        )

        response = self.client.get(
            "/api/investment-simulator/",
            self.simulation_params(symbol="MSFT"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["available_observations"],
            0,
        )