from django.urls import path
from . import views

app_name = "moderation"

urlpatterns = [
    path("", views.moderation_home, name="home"),
    path("queue/", views.moderation_queue, name="queue"),
    path("log/", views.moderation_log, name="log"),

    path("decision/", include(("apps.moderation.decision_row.urls", "decision_row"), namespace="decision_row")),
]
