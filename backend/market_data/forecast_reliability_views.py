"""Authenticated, read-only published historical diagnostics.

No database access, provider fetches, model training or forecast capture occurs
from this endpoint. Evidence is versioned with the code being served.
"""
import json
from pathlib import Path

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

SNAPSHOT = Path(__file__).with_name("research_reliability_snapshot.json")


def load_reliability_snapshot(path=SNAPSHOT):
    result = json.loads(Path(path).read_text(encoding="utf-8"))
    if (
        result.get("kind") != "historical_research_snapshot"
        or result.get("dataset_role") != "development_diagnostic_not_independent_holdout"
        or result.get("promotion_approved") is not False
        or not result.get("stocks")
    ):
        raise ValueError("Historical research evidence failed provenance validation.")
    return result


class ForecastReliabilityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = Response(load_reliability_snapshot())
        response["Cache-Control"] = "private, no-store"
        return response
