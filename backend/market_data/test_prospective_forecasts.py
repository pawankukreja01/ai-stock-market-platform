"""Prospective journal integrity, chronology and database safety."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch
import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.utils import timezone as dj_timezone
from rest_framework.response import Response

from market_data.models import HistoricalPrice, ProspectiveForecast
from market_data.prospective_evaluation import (
    forecast_skill_summary, prospective_outcome,
)
from stocks.models import Stock


class ProspectiveChronologyTests(SimpleTestCase):
    def setUp(self):
        self.base = date(2026, 11, 2)
        self.forecast = SimpleNamespace(
            signal_date=self.base, horizon=2, scored_at=None,
            created_at=datetime(2026, 11, 2, 20, tzinfo=timezone.utc),
        )
        dates = [
            date(2026, 11, 3), date(2026, 11, 4),
            date(2026, 11, 5), date(2026, 11, 6),
        ]
        self.rows = [
            {"date": day, "close_price": Decimal(100 + index * 5),
             "is_ohlc_valid": True}
            for index, day in enumerate(dates)
        ]

    def test_evaluates_next_close_entry_and_horizon_exit(self):
        result = prospective_outcome(
            self.forecast, self.rows, today=date(2026, 11, 6)
        )
        self.assertEqual(result["entry_date"], date(2026, 11, 3))
        self.assertEqual(result["exit_date"], date(2026, 11, 5))
        self.assertEqual(result["entry_price"], 100)
        self.assertEqual(result["exit_price"], 110)
        self.assertEqual(result["realized_return"], Decimal("0.1000000000"))

    def test_no_lookahead_before_exit_or_on_invalid_session(self):
        self.assertIsNone(prospective_outcome(
            self.forecast, self.rows, today=date(2026, 11, 4)
        ))
        corrupted = [dict(x) for x in self.rows]
        corrupted[1]["is_ohlc_valid"] = False
        self.assertIsNone(prospective_outcome(
            self.forecast, corrupted, today=date(2026, 11, 6)
        ))

    def test_late_issued_forecast_is_never_scored(self):
        late = SimpleNamespace(**vars(self.forecast))
        late.created_at = datetime(2026, 11, 3, 22, tzinfo=timezone.utc)
        self.assertIsNone(prospective_outcome(
            late, self.rows, today=date(2026, 11, 6)
        ))

    def test_empty_performance_does_not_claim_skill(self):
        result = forecast_skill_summary([])
        self.assertIsNone(result["beats_zero_baseline"])
        self.assertEqual(result["evaluated"], 0)

    def test_zero_baseline_comparison_on_same_matured_records(self):
        records = [
            SimpleNamespace(
                realized_return=Decimal("0.04"),
                predicted_return=Decimal("0.03"),
                lower_return=Decimal("0"),
                upper_return=Decimal("0.06"),
            ),
            SimpleNamespace(
                realized_return=Decimal("-0.02"),
                predicted_return=Decimal("-0.03"),
                lower_return=Decimal("-0.06"),
                upper_return=Decimal("0"),
            ),
        ]
        result = forecast_skill_summary(records)
        self.assertTrue(result["beats_zero_baseline"])
        self.assertEqual(result["evaluated"], 2)
        self.assertEqual(result["direction_accuracy"], 1.0)


class ProspectiveAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user(
            username="forecast-admin", password="secure-test-pass",
            is_staff=True,
        )
        cls.viewer = get_user_model().objects.create_user(
            username="forecast-viewer", password="secure-test-pass",
        )
        cls.stock = Stock.objects.create(
            symbol="AAPL", company_name="Apple", exchange="NASDAQ",
            is_active=True,
        )

    def test_guest_cannot_read_or_capture(self):
        self.assertIn(
            self.client.get("/api/prospective-forecasts/results/").status_code,
            (401, 403),
        )
        self.assertIn(
            self.client.post("/api/prospective-forecasts/capture/").status_code,
            (401, 403),
        )

    def test_nonstaff_cannot_issue_prediction(self):
        self.client.force_login(self.viewer)
        response = self.client.post("/api/prospective-forecasts/capture/", {
            "symbol": "AAPL",
        })
        self.assertEqual(response.status_code, 403)

    def test_guard_blocks_original_db_before_model_training(self):
        self.client.force_login(self.staff)
        with patch.dict(os.environ, {"DB_NAME": "ai_stock_market"}):
            response = self.client.post(
                "/api/prospective-forecasts/capture/", {"symbol": "AAPL"}
            )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ProspectiveForecast.objects.exists())

    def test_cannot_record_stale_or_future_observation(self):
        self.client.force_login(self.staff)
        with (
            patch("market_data.prospective_views.can_write_test_forecast",
                  return_value=True),
            patch("market_data.prospective_views.MLReturnPredictionView.get",
                  return_value=Response({
                      "historical_period": {"end_date": "2021-11-03"},
                      "prediction": {"return": 0.05,
                                     "lower_return": 0,
                                     "upper_return": 0.1},
                      "confidence": 0.9,
                  })),
        ):
            response = self.client.post(
                "/api/prospective-forecasts/capture/",
                {"symbol": "AAPL", "horizon": 5, "model": "random_forest"},
            )
        self.assertEqual(response.status_code, 422)
        self.assertFalse(ProspectiveForecast.objects.exists())

    def test_model_generated_forecast_recorded_once(self):
        self.client.force_login(self.staff)
        prediction = {
            "historical_period": {"end_date": dj_timezone.localdate().isoformat()},
            "prediction": {"return": 0.03,
                           "lower_return": -0.02,
                           "upper_return": 0.07},
            "confidence": 0.9,
        }
        with (
            patch("market_data.prospective_views.can_write_test_forecast",
                  return_value=True),
            patch("market_data.prospective_views.MLReturnPredictionView.get",
                  return_value=Response(prediction)),
        ):
            first = self.client.post(
                "/api/prospective-forecasts/capture/",
                {"symbol": "AAPL", "horizon": 5},
            )
            second = self.client.post(
                "/api/prospective-forecasts/capture/",
                {"symbol": "AAPL", "horizon": 5},
            )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(ProspectiveForecast.objects.count(), 1)
        self.assertEqual(
            ProspectiveForecast.objects.first().predicted_return,
            Decimal("0.03"),
        )

    def test_read_only_results_show_pending_without_claiming_skill(self):
        self.client.force_login(self.viewer)
        response = self.client.get("/api/prospective-forecasts/results/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["metrics"]["evaluated"], 0)
        self.assertIsNone(response.json()["metrics"]["beats_zero_baseline"])

    def test_settlement_refuses_unspecified_database(self):
        with patch.dict(os.environ, {"DB_NAME": "ai_stock_market"}):
            with self.assertRaisesRegex(CommandError, "requires explicit|Requires explicit"):
                call_command(
                    "evaluate_prospective_forecasts",
                    stdout=StringIO(),
                )
