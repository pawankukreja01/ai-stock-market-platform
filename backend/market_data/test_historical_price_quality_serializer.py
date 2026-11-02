from datetime import date
from decimal import Decimal

from django.test import TestCase

from market_data.models import HistoricalPrice
from market_data.serializers import HistoricalPriceSerializer
from stocks.models import Stock


class HistoricalPriceQualitySerializerTests(TestCase):
    def test_serializer_exposes_currency_and_quality_metadata(self):
        stock = Stock.objects.create(
            symbol="SERIALIZER_TEST",
            company_name="Serializer Test Inc.",
            exchange="NASDAQ",
            sector="Technology",
            industry="Software",
            is_active=True,
        )
        price = HistoricalPrice.objects.create(
            stock=stock,
            date=date(2026, 10, 30),
            open_price=Decimal("10.00"),
            high_price=Decimal("11.00"),
            low_price=Decimal("9.00"),
            close_price=Decimal("10.50"),
            adjusted_close=Decimal("10.50"),
            volume=1000,
            provider_currency="USD",
            storage_currency="USD",
            is_ohlc_valid=True,
            is_volume_valid=True,
            quality_flags={"source": "test"},
        )

        data = HistoricalPriceSerializer(price).data

        self.assertEqual(data["provider_currency"], "USD")
        self.assertEqual(data["storage_currency"], "USD")
        self.assertTrue(data["is_ohlc_valid"])
        self.assertTrue(data["is_volume_valid"])
        self.assertEqual(data["quality_flags"], {"source": "test"})
