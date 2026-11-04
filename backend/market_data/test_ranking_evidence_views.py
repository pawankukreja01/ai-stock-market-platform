"""Historical stock-ranking evidence never masquerades as prediction accuracy."""
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from market_data.ranking_evidence_views import RankingEvidenceView, load_ranking_evidence_snapshot


class RankingEvidenceTests(SimpleTestCase):
    def test_snapshot_matches_uploaded_replay_and_no_accuracy_claims(self):
        r = load_ranking_evidence_snapshot()
        self.assertEqual(r["source_sha256"],
                         "1fba17df2f706cc9f26ddd9b7f73496b97fb0ecfec169c6953367cd9a48b853f")
        self.assertEqual(r["summary"]["evaluated_periods"], 26)
        self.assertEqual(r["summary"]["excluded_periods"], 2)
        self.assertEqual(r["summary"]["wins"], 13)
        self.assertEqual(r["summary"]["losses"], 13)
        self.assertEqual(r["summary"]["baseline_relative_win_rate"], 0.5)
        self.assertAlmostEqual(r["summary"]["mean_excess_return_percentage_points"], 0.3894055)
        self.assertAlmostEqual(r["summary"]["median_excess_return_percentage_points"], -0.029559)
        self.assertEqual([x["wins"] for x in r["by_year"]], [8, 5, 0])
        self.assertFalse(r["approved_to_claim_recommendation_accuracy"])
        self.assertFalse(r["approved_for_live_model_promotion"])
        self.assertIsNone(r["summary"]["prediction_accuracy"])
        self.assertIsNone(r["summary"]["win_probability_calibrated"])

    def test_unauthenticated_access_rejected(self):
        response = RankingEvidenceView.as_view()(
            APIRequestFactory().get("/api/ranking-evidence/")
        )
        self.assertIn(response.status_code, (401, 403))

    def test_authenticated_snapshot_is_read_only(self):
        request = APIRequestFactory().get("/api/ranking-evidence/")
        force_authenticate(request, user=get_user_model()(username="reader"))
        response = RankingEvidenceView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response.data["summary"]["wins"], 13)
