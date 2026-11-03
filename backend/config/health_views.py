"""Minimal deployment liveness and database readiness checks.

Never accesses provider endpoints, secret values or personal user records.
"""
from django.db import connections
from django.http import JsonResponse


def liveness(request):
    response = JsonResponse({"status": "ok", "service": "marketpulse-api"})
    response["Cache-Control"] = "no-store"
    return response


def database_readiness(request):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            if cursor.fetchone()[0] != 1:
                raise ValueError("Unexpected database response")
    except Exception:
        result = JsonResponse({"status": "unavailable"}, status=503)
    else:
        result = JsonResponse({"status": "ready"})
    result["Cache-Control"] = "no-store"
    return result
