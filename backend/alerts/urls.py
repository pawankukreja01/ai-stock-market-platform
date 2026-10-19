from django.urls import path

from .views import (
    AlertRuleListCreateView,
    AlertRuleDetailView,
    AlertEventListView,
    AlertEventMarkReadView,
)


urlpatterns = [
    path(
        "alerts/",
        AlertRuleListCreateView.as_view(),
        name="alert-list-create",
    ),
    path(
        "alerts/events/",
        AlertEventListView.as_view(),
        name="alert-event-list",
    ),
    path(
        "alerts/events/<int:pk>/read/",
        AlertEventMarkReadView.as_view(),
        name="alert-event-mark-read",
    ),
    path(
        "alerts/<int:pk>/",
        AlertRuleDetailView.as_view(),
        name="alert-detail",
    ),
]