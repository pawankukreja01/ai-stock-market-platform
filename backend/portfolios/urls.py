from django.urls import path

from .views import (
    PortfolioListCreateView,
    PortfolioDetailView,
    PortfolioHoldingListCreateView,
    PortfolioHoldingDetailView,
    PortfolioAnalysisView,
)


urlpatterns = [
    path(
        "portfolios/",
        PortfolioListCreateView.as_view(),
        name="portfolio-list-create",
    ),
    path(
        "portfolios/<int:pk>/",
        PortfolioDetailView.as_view(),
        name="portfolio-detail",
    ),
    path(
        "portfolios/<int:portfolio_id>/holdings/",
        PortfolioHoldingListCreateView.as_view(),
        name="portfolio-holdings",
    ),
    path(
        "portfolios/<int:portfolio_id>/holdings/<int:pk>/",
        PortfolioHoldingDetailView.as_view(),
        name="portfolio-holding-detail",
    ),
    path(
        "portfolios/<int:portfolio_id>/analysis/",
        PortfolioAnalysisView.as_view(),
        name="portfolio-analysis",
    ),
]