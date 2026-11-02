from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient

from market_data.models import HistoricalPrice, NewsArticle
from stocks.models import Stock

from .models import AlertEvent, AlertRule
from alerts.management.commands.evaluate_alerts import get_observed_value


class AlertAPITests(TestCase):
    """Test alert creation, validation, and event management."""

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

        HistoricalPrice.objects.create(
            stock=self.stock,
            date=date(2026, 10, 16),
            open_price=Decimal("340.00"),
            high_price=Decimal("345.00"),
            low_price=Decimal("338.00"),
            close_price=Decimal("343.46"),
            adjusted_close=Decimal("343.46"),
            volume=1000000,
        )

    def create_rule(
        self,
        alert_type=AlertRule.PRICE_ABOVE,
        threshold="300.00",
        name="Test AAPL alert",
    ):
        return AlertRule.objects.create(
            stock=self.stock,
            name=name,
            alert_type=alert_type,
            threshold=Decimal(threshold),
            is_active=True,
        )

    def test_create_price_alert(self):
        response = self.client.post(
            "/api/alerts/",
            {
                "stock_symbol": "AAPL",
                "name": "AAPL above 300",
                "alert_type": "price_above",
                "threshold": "300.00",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["stock_symbol"], "AAPL")
        self.assertEqual(response.data["alert_type"], "price_above")
        self.assertTrue(
            AlertRule.objects.filter(
                stock=self.stock,
                threshold=Decimal("300.00"),
            ).exists()
        )

    def test_reject_invalid_sentiment_threshold(self):
        response = self.client.post(
            "/api/alerts/",
            {
                "stock_symbol": "AAPL",
                "name": "Invalid sentiment alert",
                "alert_type": "sentiment_above",
                "threshold": "1.50",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("threshold", response.data)

    def test_reject_non_positive_price_threshold(self):
        response = self.client.post(
            "/api/alerts/",
            {
                "stock_symbol": "AAPL",
                "name": "Invalid price alert",
                "alert_type": "price_below",
                "threshold": "0",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_price_alert_ignores_non_positive_latest_close(self):
        rule = self.create_rule(
            alert_type=AlertRule.PRICE_ABOVE,
            threshold="300.00",
        )

        HistoricalPrice.objects.create(
            stock=self.stock,
            date=date(2026, 10, 17),
            open_price=Decimal("0.00"),
            high_price=Decimal("0.00"),
            low_price=Decimal("0.00"),
            close_price=Decimal("0.00"),
            adjusted_close=Decimal("0.00"),
            volume=0,
            is_ohlc_valid=False,
            is_volume_valid=True,
            quality_flags={"ohlc": "non_positive_close"},
        )

        self.assertEqual(
            get_observed_value(rule),
            Decimal("343.46"),
        )

    def test_evaluator_triggers_price_alert_once(self):
        rule = self.create_rule(
            alert_type=AlertRule.PRICE_ABOVE,
            threshold="300.00",
        )

        first_output = StringIO()

        call_command(
            "evaluate_alerts",
            symbol="AAPL",
            stdout=first_output,
        )

        self.assertEqual(
            AlertEvent.objects.filter(rule=rule).count(),
            1,
        )
        rule.refresh_from_db()
        self.assertTrue(rule.condition_met)

        second_output = StringIO()

        call_command(
            "evaluate_alerts",
            symbol="AAPL",
            stdout=second_output,
        )

        # The condition is still true, so the second evaluation
        # must not create another event for this rule.
        self.assertEqual(
            AlertEvent.objects.filter(rule=rule).count(),
            1,
        )
        self.assertIn(
            "New events triggered: 0",
            second_output.getvalue(),
        )

    def test_price_alert_resets_when_condition_no_longer_met(self):
        rule = self.create_rule(
            alert_type=AlertRule.PRICE_ABOVE,
            threshold="300.00",
        )

        call_command(
            "evaluate_alerts",
            symbol="AAPL",
            stdout=StringIO(),
        )

        self.assertEqual(
            AlertEvent.objects.filter(rule=rule).count(),
            1,
        )

        # Change the latest stored close to below the threshold.
        price = HistoricalPrice.objects.get(
            stock=self.stock,
            date=date(2026, 10, 16),
        )
        price.close_price = Decimal("250.00")
        price.save(update_fields=["close_price"])

        call_command(
            "evaluate_alerts",
            symbol="AAPL",
            stdout=StringIO(),
        )

        rule.refresh_from_db()
        self.assertFalse(rule.condition_met)

        # Return the price above the threshold. A new crossing
        # should create a new event.
        price.close_price = Decimal("320.00")
        price.save(update_fields=["close_price"])

        call_command(
            "evaluate_alerts",
            symbol="AAPL",
            stdout=StringIO(),
        )

        self.assertEqual(
            AlertEvent.objects.filter(rule=rule).count(),
            2,
        )

    def test_sentiment_alert_uses_analyzed_news(self):
        NewsArticle.objects.create(
            stock=self.stock,
            title="Positive company outlook",
            url="https://example.com/news/aapl-positive",
            summary="A test article with a positive sentiment score.",
            published_at=timezone.now(),
            sentiment_label="positive",
            sentiment_score=0.60,
            sentiment_analyzed_at=timezone.now(),
            sentiment_model="test-model",
        )

        rule = self.create_rule(
            alert_type=AlertRule.SENTIMENT_ABOVE,
            threshold="0.50",
            name="Positive sentiment",
        )

        call_command(
            "evaluate_alerts",
            rule_id=rule.id,
            stdout=StringIO(),
        )

        self.assertEqual(
            AlertEvent.objects.filter(rule=rule).count(),
            1,
        )

        rule.refresh_from_db()
        self.assertTrue(rule.condition_met)

    def test_unread_events_can_be_marked_read(self):
        rule = self.create_rule()

        event = AlertEvent.objects.create(
            rule=rule,
            observed_value=Decimal("343.46"),
            message="Test alert event",
        )

        response = self.client.get(
            "/api/alerts/events/?unread=true"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        response = self.client.post(
            f"/api/alerts/events/{event.id}/read/",
            {"is_read": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        event.refresh_from_db()
        self.assertTrue(event.is_read)

        unread_response = self.client.get(
            "/api/alerts/events/?unread=true"
        )
        self.assertEqual(unread_response.data["count"], 0)

        read_response = self.client.get(
            "/api/alerts/events/?unread=false"
        )
        self.assertEqual(read_response.data["count"], 1)

    def test_inactive_rule_is_not_evaluated(self):
        rule = self.create_rule()
        rule.is_active = False
        rule.save(update_fields=["is_active"])

        output = StringIO()

        call_command(
            "evaluate_alerts",
            symbol="AAPL",
            stdout=output,
        )

        self.assertEqual(
            AlertEvent.objects.filter(rule=rule).count(),
            0,
        )