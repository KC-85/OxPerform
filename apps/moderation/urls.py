from django.urls import path, include
from . import views

app_name = "moderation"

urlpatterns = [
    path("", views.moderation_home, name="home"),
    path("log/", views.moderation_log, name="log"),

    # Queue app
    path("queue/", include(("apps.moderation.queue.urls", "queue"), namespace="queue")),

    # Decision row app
    path("decision/", include(("apps.moderation.decision_row.urls", "decision_row"), namespace="decision_row")),
]
