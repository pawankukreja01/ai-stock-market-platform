from django.urls import path
from .screener_views import StockScreenerView
from .investment_simulator_views import InvestmentSimulatorView

from .views import (
    HistoricalPriceListView,
    BenchmarkComparisonView,
    FundamentalListView,
    RiskMetricsView,
)

from .ml_views import (
    MLReturnPredictionView,
)

from .backtesting_views import (
    BacktestView,
)

from .news_views import NewsArticleListView

from .sentiment_views import StockSentimentSummaryView

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

    path(
        "ml-prediction/",
        MLReturnPredictionView.as_view(),
        name="ml-prediction",
    ),

    path(
        "backtest/",
        BacktestView.as_view(),
        name="backtest",
    ),

    path(
        "news/",
        NewsArticleListView.as_view(),
        name="news",
    ),

    path(
    "sentiment/",
    StockSentimentSummaryView.as_view(),
    name="sentiment-summary",
    ),

    path(
    "screener/",
    StockScreenerView.as_view(),
    name="stock-screener",
    ),

    path(
    "investment-simulator/",
    InvestmentSimulatorView.as_view(),
    name="investment-simulator",
),
]
