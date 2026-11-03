from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from stocks.models import Stock


class StockCatalogAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/stocks/"

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
        self.azn = Stock.objects.create(
            symbol="AZN.L",
            company_name="AstraZeneca PLC",
            exchange="LSE",
            sector="Healthcare",
            industry="Pharmaceuticals",
            is_active=True,
        )
        self.other = Stock.objects.create(
            symbol="ZZTOP",
            company_name="Test Industries",
            exchange="NYSE",
            sector="Industrials",
            industry="Manufacturing",
            is_active=True,
        )
        self.inactive = Stock.objects.create(
            symbol="INACTIVE",
            company_name="Inactive Test Company",
            exchange="NASDAQ",
            sector="Technology",
            industry="Software",
            is_active=False,
        )

    @staticmethod
    def symbols(response):
        data = response.data
        if isinstance(data, dict):
            data = data["results"]
        return [item["symbol"] for item in data]

    def test_list_returns_array_by_default_and_only_active_stocks(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertIn("AAPL", self.symbols(response))
        self.assertNotIn("INACTIVE", self.symbols(response))

    def test_search_matches_symbol_and_company_case_insensitively(self):
        by_company = self.client.get(self.url, {"search": "apple"})
        by_symbol = self.client.get(self.url, {"search": "azn.l"})

        self.assertEqual(by_company.status_code, 200)
        self.assertEqual(self.symbols(by_company), ["AAPL"])
        self.assertEqual(self.symbols(by_symbol), ["AZN.L"])

    def test_market_filter_separates_us_and_uk(self):
        us_response = self.client.get(self.url, {"market": "US"})
        uk_response = self.client.get(self.url, {"market": "UK"})

        self.assertEqual(us_response.status_code, 200)
        self.assertEqual(uk_response.status_code, 200)
        self.assertEqual(set(self.symbols(us_response)), {"AAPL", "MSFT", "ZZTOP"})
        self.assertEqual(self.symbols(uk_response), ["AZN.L"])

    def test_exchange_and_sector_filters_can_be_combined(self):
        response = self.client.get(
            self.url,
            {"exchange": "NASDAQ", "sector": "Technology"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(self.symbols(response)), {"AAPL", "MSFT"})

    def test_invalid_market_returns_bad_request(self):
        response = self.client.get(self.url, {"market": "Mars"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_serializer_reports_market_and_popular_status(self):
        response = self.client.get(self.url, {"search": "AAPL"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["market"], "US")
        self.assertTrue(response.data[0]["is_popular"])

        uk_response = self.client.get(self.url, {"search": "AZN.L"})
        self.assertEqual(uk_response.data[0]["market"], "UK")

    def test_popular_endpoint_only_returns_curated_symbols(self):
        response = self.client.get(f"{self.url}popular/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(self.symbols(response)), {"AAPL", "MSFT", "AZN.L"})

    def test_popular_endpoint_respects_market_filter(self):
        response = self.client.get(
            f"{self.url}popular/",
            {"market": "UK"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.symbols(response), ["AZN.L"])

    def test_pagination_is_available_when_requested(self):
        response = self.client.get(
            self.url,
            {"page": 1, "page_size": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 4)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["page_size"], 2)

    def test_seed_command_is_idempotent(self):
        call_command("seed_stock_universe", verbosity=0)
        count_after_first_run = Stock.objects.count()

        call_command("seed_stock_universe", verbosity=0)
        count_after_second_run = Stock.objects.count()

        self.assertEqual(count_after_first_run, count_after_second_run)
        self.assertEqual(Stock.objects.filter(symbol="SHEL.L").count(), 1)
        self.assertEqual(Stock.objects.filter(symbol="AAPL").count(), 1)

    def test_seed_dry_run_does_not_write_stock_records(self):
        count_before = Stock.objects.count()

        call_command("seed_stock_universe", dry_run=True, verbosity=0)

        self.assertEqual(Stock.objects.count(), count_before)
        self.assertFalse(Stock.objects.filter(symbol="SHEL.L").exists())

    def test_stock_catalogue_cannot_be_created_modified_or_deleted_over_api(self):
        stock_count = Stock.objects.count()
        create = self.client.post(self.url, {
            "symbol": "ATTACK", "company_name": "Unauthorized",
            "exchange": "NASDAQ",
        }, format="json")
        self.assertEqual(create.status_code, 405)
        update = self.client.patch(
            f"{self.url}{self.aapl.pk}/",
            {"company_name": "Changed without permission"},
            format="json",
        )
        self.assertEqual(update.status_code, 405)
        delete = self.client.delete(f"{self.url}{self.aapl.pk}/")
        self.assertEqual(delete.status_code, 405)
        self.assertEqual(Stock.objects.count(), stock_count)
        self.aapl.refresh_from_db()
        self.assertEqual(self.aapl.company_name, "Apple Inc.")

    def test_inactive_stock_detail_is_not_public(self):
        response = self.client.get(f"{self.url}{self.inactive.pk}/")
        self.assertEqual(response.status_code, 404)
