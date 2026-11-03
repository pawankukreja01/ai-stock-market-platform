from datetime import date

from django.test import SimpleTestCase

from market_data.management.commands.audit_prediction_prices import audit_price_rows


class PredictionPriceAuditTests(SimpleTestCase):
    def make_row(self, when, close, adjusted, *, ohlc=True, volume=True):
        return {
            "date": date.fromisoformat(when),
            "close_price": close,
            "adjusted_close": adjusted,
            "is_ohlc_valid": ohlc,
            "is_volume_valid": volume,
        }

    def test_clean_prices_have_no_flags(self):
        rows = [
            self.make_row("2026-10-28", 100, 95),
            self.make_row("2026-10-29", 101, 95.95),
            self.make_row("2026-10-30", 102, 96.90),
        ]
        report = audit_price_rows(rows, today=date(2026, 11, 3))
        self.assertEqual(report["observations"], 3)
        self.assertEqual(report["large_close_move_count"], 0)
        self.assertEqual(report["large_adjustment_factor_change_count"], 0)

    def test_flags_large_jump_and_factor_shift_without_rewriting(self):
        rows = [
            self.make_row("2026-10-28", 100, 100),
            self.make_row("2026-10-29", 45, 90),
        ]
        report = audit_price_rows(rows, today=date(2026, 11, 3))
        self.assertEqual(report["large_close_move_count"], 1)
        self.assertEqual(report["large_adjustment_factor_change_count"], 1)
        self.assertEqual(rows[1]["close_price"], 45)

    def test_invalid_rows_prevent_bridging_and_future_dates_flagged(self):
        rows = [
            self.make_row("2026-10-28", 100, 95),
            self.make_row("2026-10-29", 80, 76, ohlc=False, volume=False),
            self.make_row("2026-11-04", 40, 38),
        ]
        report = audit_price_rows(rows, today=date(2026, 11, 3))
        self.assertEqual(report["ohlc_invalid"], 1)
        self.assertEqual(report["volume_invalid"], 1)
        self.assertEqual(report["future_dated_rows"], 1)
        self.assertEqual(report["large_close_move_count"], 0)

    def test_rejects_unsorted_dates(self):
        rows = [
            self.make_row("2026-10-29", 100, 95),
            self.make_row("2026-10-28", 101, 96),
        ]
        with self.assertRaisesRegex(ValueError, "date-ordered"):
            audit_price_rows(rows, today=date(2026, 11, 3))
