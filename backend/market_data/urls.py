from django.urls import path

from .views import (
    HistoricalPriceListView,
    BenchmarkComparisonView,
    FundamentalListView,
    RiskMetricsView,
)


urlpatterns = [
    path(
        "historical-prices/",
        HistoricalPriceListView.as_view(),
        name="historical-prices",
    ),

    path(
        "benchmark-comparison/",
        BenchmarkComparisonView.as_view(),
        name="benchmark-comparison",
    ),

    path(
        "fundamentals/",
        FundamentalListView.as_view(),
        name="fundamentals",
    ),

    path(
        "risk-metrics/",
        RiskMetricsView.as_view(),
        name="risk-metrics",
    ),
]