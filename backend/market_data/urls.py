from django.urls import path
from .screener_views import StockScreenerView
from .investment_simulator_views import InvestmentSimulatorView
from .quote_views import LatestQuoteView
from .research_readiness_views import ResearchReadinessView
from .market_data_coverage_views import MarketDataCoverageView
from .prospective_views import ProspectiveCaptureView, ProspectiveResultsView

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
from .recommendation_views import StockRecommendationsView

urlpatterns = [
    path("market-data-coverage/", MarketDataCoverageView.as_view(), name="market-data-coverage"),
    path("prospective-forecasts/capture/", ProspectiveCaptureView.as_view(), name="prospective-capture"),
    path("prospective-forecasts/results/", ProspectiveResultsView.as_view(), name="prospective-results"),
    path("research-readiness/", ResearchReadinessView.as_view(), name="research-readiness"),
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
    path(
        "recommendations/",
        StockRecommendationsView.as_view(),
        name="stock-recommendations",
    ),
    path(
    "quotes/<str:symbol>/",
    LatestQuoteView.as_view(),
    name="latest-stock-quote",
    ),
]
