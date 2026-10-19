
from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from market_data.models import Fundamental
from stocks.models import Stock


class StockScreenerAPITests(TestCase):
    """Test the stock screener API, filters, sorting, and pagination."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/screener/"

        self.aapl = Stock.objects.create(
            symbol="AAPL",
            company_name="Apple Inc.",
            exchange="NASDAQ",
            sector="Technology",
            industry="Consumer Electronics",
            is_active=True,
        )

        self.msft = Stock.objects.create(
            symbol="MSFT",
            company_name="Microsoft Corporation",
            exchange="NASDAQ",
            sector="Technology",
            industry="Software",
            is_active=True,
        )

        self.jpm = Stock.objects.create(
            symbol="JPM",
            company_name="JPMorgan Chase & Co.",
            exchange="NYSE",
            sector="Financial Services",
            industry="Banking",
            is_active=True,
        )

        self.inactive = Stock.objects.create(
            symbol="ZZZ",
            company_name="Inactive Test Corporation",
            exchange="NASDAQ",
            sector="Technology",
            industry="Software",
            is_active=False,
        )

        # Synthetic fundamentals for deterministic tests.
        self.add_fundamental(
            self.aapl,
            date(2025, 12, 31),
            "annual",
            "30",
            "0.25",
            "0.20",
        )

        self.add_fundamental(
            self.aapl,
            date(2026, 3, 31),
            "quarterly",
            "32",
            "0.26",
            "0.21",
        )

        self.add_fundamental(
            self.msft,
            date(2025, 12, 31),
            "annual",
            "35",
            "0.30",
            "0.35",
        )

        self.add_fundamental(
            self.jpm,
            date(2025, 12, 31),
            "annual",
            "12",
            "0.15",
            "0.18",
        )

    def add_fundamental(
        self,
        stock,
        period_end,
        period_type,
        pe_ratio,
        roe,
        profit_margin,
    ):
        return Fundamental.objects.create(
            stock=stock,
            period_end=period_end,
            period_type=period_type,
            pe_ratio=Decimal(pe_ratio),
            roe=Decimal(roe),
            profit_margin=Decimal(profit_margin),
        )

    def get_symbols(self, response):
        return [row["symbol"] for row in response.data["results"]]

    def test_returns_only_active_stocks(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(
            self.get_symbols(response),
            ["AAPL", "JPM", "MSFT"],
        )
        self.assertNotIn(
            "ZZZ",
            self.get_symbols(response),
        )

    def test_response_contains_expected_fields(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        apple = next(
            row for row in response.data["results"]
            if row["symbol"] == "AAPL"
        )

        for field in (
            "symbol",
            "company_name",
            "exchange",
            "sector",
            "industry",
            "price",
            "pe_ratio",
            "roe",
            "profit_margin",
            "technical_data_available",
        ):
            self.assertIn(field, apple)

        self.assertEqual(apple["company_name"], "Apple Inc.")
        self.assertAlmostEqual(apple["pe_ratio"], 32.0)

    def test_search_is_case_insensitive(self):
        response = self.client.get(
            self.url,
            {"search": "MICROSOFT"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_symbols(response), ["MSFT"])

    def test_sector_and_exchange_filters(self):
        response = self.client.get(
            self.url,
            {
                "sector": "tech",
                "exchange": "nasdaq",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.get_symbols(response),
            ["AAPL", "MSFT"],
        )

    def test_filters_by_maximum_pe_ratio(self):
        response = self.client.get(
            self.url,
            {"max_pe_ratio": "20"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_symbols(response), ["JPM"])
        self.assertAlmostEqual(
            response.data["results"][0]["pe_ratio"],
            12.0,
        )

    def test_filters_by_minimum_pe_ratio(self):
        response = self.client.get(
            self.url,
            {"min_pe_ratio": "32"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.get_symbols(response),
            ["AAPL", "MSFT"],
        )

    def test_selects_requested_fundamental_period(self):
        response = self.client.get(
            self.url,
            {"period_type": "annual"},
        )

        self.assertEqual(response.status_code, 200)

        results = {
            row["symbol"]: row
            for row in response.data["results"]
        }

        self.assertAlmostEqual(results["AAPL"]["pe_ratio"], 30.0)
        self.assertEqual(
            results["AAPL"]["fundamental_period_type"],
            "annual",
        )

    def test_sorts_pe_ratio_ascending_and_descending(self):
        ascending = self.client.get(
            self.url,
            {
                "sort_by": "pe_ratio",
                "sort_order": "asc",
            },
        )

        descending = self.client.get(
            self.url,
            {
                "sort_by": "pe_ratio",
                "sort_order": "desc",
            },
        )

        self.assertEqual(ascending.status_code, 200)
        self.assertEqual(descending.status_code, 200)

        self.assertEqual(
            self.get_symbols(ascending),
            ["JPM", "AAPL", "MSFT"],
        )

        self.assertEqual(
            self.get_symbols(descending),
            ["MSFT", "AAPL", "JPM"],
        )

        self.assertEqual(
            ascending.data["sort"]["order"],
            "asc",
        )
        self.assertEqual(
            descending.data["sort"]["order"],
            "desc",
        )

    def test_pagination_returns_correct_page(self):
        response = self.client.get(
            self.url,
            {
                "sort_by": "symbol",
                "page": "2",
                "page_size": "2",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(response.data["page"], 2)
        self.assertEqual(response.data["page_size"], 2)
        self.assertEqual(response.data["total_pages"], 2)
        self.assertEqual(self.get_symbols(response), ["MSFT"])

    def test_rejects_invalid_fundamental_period(self):
        response = self.client.get(
            self.url,
            {"period_type": "monthly"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_rejects_non_numeric_filter(self):
        response = self.client.get(
            self.url,
            {"min_price": "not-a-number"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_rejects_infinite_numeric_filter(self):
        response = self.client.get(
            self.url,
            {"max_price": "inf"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_rejects_inverted_pe_range(self):
        response = self.client.get(
            self.url,
            {
                "min_pe_ratio": "40",
                "max_pe_ratio": "20",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_rejects_unsupported_sort_field(self):
        response = self.client.get(
            self.url,
            {"sort_by": "unsupported_field"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_rejects_invalid_sort_order(self):
        response = self.client.get(
            self.url,
            {"sort_order": "sideways"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_rejects_non_integer_pagination(self):
        response = self.client.get(
            self.url,
            {"page": "invalid"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_rejects_invalid_page_size(self):
        response = self.client.get(
            self.url,
            {"page_size": "101"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
