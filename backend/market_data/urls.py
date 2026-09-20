from django.urls import path

from .views import HistoricalPriceListView


urlpatterns = [
    path(
        "historical-prices/",
        HistoricalPriceListView.as_view(),
        name="historical-prices",
    ),
]