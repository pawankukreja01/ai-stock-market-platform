from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AlertRule, AlertEvent
from .serializers import AlertRuleSerializer, AlertEventSerializer


class AlertRuleListCreateView(generics.ListCreateAPIView):
    """List alert rules or create a rule."""

    serializer_class = AlertRuleSerializer

    def get_queryset(self):
        queryset = AlertRule.objects.select_related("stock")

        symbol = self.request.query_params.get("symbol", "").strip()
        alert_type = self.request.query_params.get(
            "alert_type", ""
        ).strip()
        active = self.request.query_params.get("is_active", "").strip()

        if symbol:
            queryset = queryset.filter(stock__symbol__iexact=symbol)

        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)

        if active:
            if active.lower() not in {"true", "false"}:
                return queryset.none()

            queryset = queryset.filter(
                is_active=(active.lower() == "true")
            )

        return queryset


class AlertRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, edit, or delete an alert rule."""

    queryset = AlertRule.objects.select_related("stock")
    serializer_class = AlertRuleSerializer


class AlertEventListView(APIView):
    """List triggered alert events."""

    def get(self, request):
        queryset = AlertEvent.objects.select_related(
            "rule",
            "rule__stock",
        )

        symbol = request.query_params.get("symbol", "").strip()
        unread = request.query_params.get("unread", "").strip().lower()

        if symbol:
            queryset = queryset.filter(
                rule__stock__symbol__iexact=symbol
            )

        if unread:
            if unread not in {"true", "false"}:
                return Response(
                    {"error": "unread must be true or false."},
                    status=400,
                )

            queryset = queryset.filter(is_read=(unread == "false"))
                                       
        try:
            limit = int(request.query_params.get("limit", "100"))
        except (TypeError, ValueError):
            return Response(
                {"error": "limit must be an integer."},
                status=400,
            )

        if not 1 <= limit <= 500:
            return Response(
                {"error": "limit must be between 1 and 500."},
                status=400,
            )

        total_count = queryset.count()
        results = queryset[:limit]

        return Response({
            "count": total_count,
            "limit": limit,
            "results": AlertEventSerializer(
                results,
                many=True,
            ).data,
        })


class AlertEventMarkReadView(APIView):
    """Mark one alert event as read or unread."""

    def post(self, request, pk):
        event = get_object_or_404(
            AlertEvent.objects.select_related(
                "rule",
                "rule__stock",
            ),
            pk=pk,
        )

        is_read = request.data.get("is_read", True)

        if not isinstance(is_read, bool):
            return Response(
                {"error": "is_read must be true or false."},
                status=400,
            )

        event.is_read = is_read
        event.save(update_fields=["is_read"])

        return Response(AlertEventSerializer(event).data)