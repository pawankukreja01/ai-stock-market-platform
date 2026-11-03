from datetime import date, timedelta

from django.test import SimpleTestCase

from market_data.management.commands.audit_market_readiness import (
    classify_price_history,
)


class MarketReadinessAuditTests(SimpleTestCase):
    def test_sufficient_fresh_history_passes(self):
        today = date(2026, 11, 3)
        self.assertEqual(
            classify_price_history(
                count=1200, latest_date=today - timedelta(days=1),
                today=today, minimum=300, max_age=7,
            ),
            [],
        )

    def test_missing_history_and_staleness_are_reported(self):
        today = date(2026, 11, 3)
        problems = classify_price_history(
            count=15, latest_date=today - timedelta(days=20),
            today=today, minimum=300, max_age=7,
        )
        self.assertEqual(len(problems), 2)
        self.assertIn("only 15", problems[0])
        self.assertIn("20 calendar days", problems[1])

    def test_future_dates_are_not_treated_as_fresh(self):
        today = date(2026, 11, 3)
        problems = classify_price_history(
            count=300, latest_date=today + timedelta(days=1),
            today=today, minimum=300, max_age=7,
        )
        self.assertTrue(any("future" in item for item in problems))
