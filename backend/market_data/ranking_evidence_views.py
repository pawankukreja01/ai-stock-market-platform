"""Read-only historical ranking evidence, not a live investment-accuracy metric."""
import json
from pathlib import Path
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

SNAPSHOT_FILE = Path(__file__).with_name("ranking_evidence_snapshot.json")


def load_ranking_evidence_snapshot(path=SNAPSHOT_FILE):
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    if (
        report.get("kind") != "historical_ranking_replay_snapshot"
        or report.get("approved_for_live_model_promotion") is not False
        or report.get("approved_to_claim_recommendation_accuracy") is not False
        or report.get("research_role") != "development_diagnostic_not_independent_holdout"
    ):
        raise ValueError("Ranked research evidence provenance validation failed.")
    return report


class RankingEvidenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = Response(load_ranking_evidence_snapshot())
        response["Cache-Control"] = "private, no-store"
        return response
