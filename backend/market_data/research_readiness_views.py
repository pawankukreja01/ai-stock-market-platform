"""Authenticated, cache-only research data readiness endpoint.

This is an informational overview of stored data, not a prediction-quality
or live-trading readiness certificate. It never calls external providers
or mutates the database.
"""

import json
import re
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from stocks.models import Stock


MAX_SYMBOLS = 20
DEFAULT_STOCK_LIMIT = 12
VALID_SYMBOL = re.compile(r"^[A-Z0-9.^=-]{1,20}$")


def parse_requested_symbols(raw):
    """Validate and de-duplicate a small symbol selection for read-only checks."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Enter at least one symbol, separated by commas.")
    values = [item.strip().upper() for item in raw.split(",")]
    if (
        not 1 <= len(values) <= MAX_SYMBOLS
        or any(not VALID_SYMBOL.fullmatch(item) for item in values)
    ):
        raise ValueError(
            "Enter 1–20 stock symbols separated by commas "
            "(letters, digits, period, caret, equals or hyphen)."
        )
    return list(dict.fromkeys(values))


def empty_readiness_report():
    return {
        "as_of_utc": None,
        "source": "stored MarketPulse database only",
        "read_only": True,
        "purpose": "data availability and freshness; not forecast skill",
        "summary": {
            "stocks": 0,
            "stocks_needing_attention": 0,
            "stocks_with_no_annual_statements": 0,
            "stocks_with_no_quarterly_statements": 0,
            "stocks_with_no_news_articles": 0,
        },
        "stocks": [],
        "note": "No active stocks in the catalogue. Nothing was downloaded.",
    }


class ResearchReadinessView(APIView):
    """Read-only source coverage and freshness for up to 20 active stocks."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        raw = request.query_params.get("symbols")
        if raw is not None:
            try:
                symbols = parse_requested_symbols(raw)
            except ValueError as exc:
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            symbols = list(
                Stock.objects.filter(is_active=True)
                .order_by("symbol").values_list("symbol", flat=True)[
                    :DEFAULT_STOCK_LIMIT
                ]
            )

        if not symbols:
            response = Response(empty_readiness_report())
            response["Cache-Control"] = "no-store"
            return response

        output = StringIO()
        try:
            # Reuse the existing, independently tested, entirely read-only
            # research audit rather than introduce a second set of status rules.
            call_command(
                "audit_research_health",
                symbols=symbols,
                stdout=output,
            )
        except CommandError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report = json.loads(output.getvalue())
        report["note"] = (
            "Source coverage and freshness only; market sessions approximate "
            "ordinary weekdays and omit exchange holidays and early closes. "
            "This is not prediction accuracy or permission to trade."
        )
        response = Response(report)
        response["Cache-Control"] = "no-store"
        return response
