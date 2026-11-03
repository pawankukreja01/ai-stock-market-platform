"""Staff-gated prospective ML issuance and historical outcome reporting.

The capture endpoint recalculates a forecast on the server; clients cannot
supply prediction values. Recording is opt-in, requires the restored test DB,
and rejects stale or future-dated signal observations.
"""
import os
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import connection, transaction
from django.utils import timezone
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from stocks.models import Stock
from .ml_views import MLReturnPredictionView, MODEL_FACTORIES, SUPPORTED_HORIZONS
from .models import ProspectiveForecast
from .prospective_evaluation import forecast_skill_summary

TEST_DB = "marketpulse_restored_test"


def can_write_test_forecast():
    return (
        os.environ.get("DB_NAME") == TEST_DB
        and connection.settings_dict["NAME"] == TEST_DB
    )


class ProspectiveCaptureView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ml_prediction"

    def post(self, request):
        if not can_write_test_forecast():
            return Response({
                "detail": "Forecast capture is restricted to the explicitly "
                          "selected restored test database."
            }, status=403)
        symbol = str(request.data.get("symbol", "")).upper().strip()
        model = str(request.data.get("model", "random_forest")).strip()
        try:
            horizon = int(request.data.get("horizon", 5))
        except (TypeError, ValueError):
            return Response({"detail": "Invalid horizon."}, status=400)
        if not symbol or model not in MODEL_FACTORIES or horizon not in SUPPORTED_HORIZONS:
            return Response({"detail": "Invalid symbol, model or horizon."}, status=400)
        stock = Stock.objects.filter(symbol=symbol, is_active=True).first()
        if stock is None:
            return Response({"detail": "Active stock not found."}, status=404)

        # Reuse actual server-side model generation, never caller-supplied
        # returns. This may be compute-intensive; DRF throttle applies.
        request._request.GET = request._request.GET.copy()
        request._request.GET.update({
            "symbol": symbol, "model": model, "horizon": str(horizon),
            "confidence": "0.90",
        })
        predicted = MLReturnPredictionView().get(request)
        if predicted.status_code != 200:
            return Response({
                "detail": "ML prediction was not available. No record saved.",
            }, status=422)

        data = predicted.data
        try:
            from datetime import date
            signal_date = date.fromisoformat(data["historical_period"]["end_date"])
            forecast_value = Decimal(str(data["prediction"]["return"]))
            lower = data["prediction"].get("lower_return")
            upper = data["prediction"].get("upper_return")
            lower = Decimal(str(lower)) if lower is not None else None
            upper = Decimal(str(upper)) if upper is not None else None
            confidence = Decimal(str(data["confidence"]))
        except (ValueError, KeyError, TypeError, InvalidOperation):
            return Response({"detail": "Invalid model output; no record saved."}, status=422)

        today = timezone.localdate()
        if signal_date > today or signal_date < today - timedelta(days=7):
            return Response({
                "detail": "Stored signal date is stale or in the future. "
                          "Update market data safely before issuing forecasts."
            }, status=422)
        if not forecast_value.is_finite():
            return Response({"detail": "Non-finite prediction rejected."}, status=422)

        with transaction.atomic():
            forecast, created = ProspectiveForecast.objects.get_or_create(
                stock=stock, model_key=model, horizon=horizon,
                signal_date=signal_date,
                defaults={
                    "predicted_return": forecast_value,
                    "lower_return": lower,
                    "upper_return": upper,
                    "confidence": confidence,
                },
            )
        return Response({
            "id": forecast.pk, "created": created, "symbol": symbol,
            "signal_date": forecast.signal_date.isoformat(),
            "horizon": forecast.horizon, "model": forecast.model_key,
            "predicted_return": str(forecast.predicted_return),
            "warning": "Prospective, research-only. Prediction is immutable; "
                       "outcome not yet known. No trading takes place.",
        }, status=201 if created else 200)


class ProspectiveResultsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        symbol = str(request.query_params.get("symbol", "")).upper().strip()
        forecasts = ProspectiveForecast.objects.select_related("stock")
        if symbol:
            if not Stock.objects.filter(symbol=symbol, is_active=True).exists():
                return Response({"detail": "Active stock not found."}, status=404)
            forecasts = forecasts.filter(stock__symbol=symbol)
        # The endpoint shows aggregate statistics only; not user portfolio data.
        forecasts = list(forecasts.order_by("-created_at")[:1000])
        summary = forecast_skill_summary(forecasts)
        return Response({
            "source": "server-recorded prospective forecasts; stored data only",
            "issued": len(forecasts),
            "pending": sum(f.scored_at is None for f in forecasts),
            "metrics": summary,
            "warning": "These are research-only, limited-sample results. "
                       "MAE and directional skill do not establish profitability. "
                       "Returns exclude dividends, fees and slippage.",
        })
