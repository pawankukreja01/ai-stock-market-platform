from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from .health_views import liveness, database_readiness


urlpatterns = [
    path("api/health/live/", liveness, name="health-live"),
    path("api/health/ready/", database_readiness, name="health-ready"),
    path("admin/", admin.site.urls),
    path("api/", include("stocks.urls")),
    path("api/", include("market_data.urls")),
    path("api/", include("portfolios.urls")),
    path("api/", include("alerts.urls")),
    path("api/auth/", include("accounts.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
