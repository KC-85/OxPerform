from django.urls import include, path

app_name = "moderation"

urlpatterns = [
    path("", include("apps.moderation.dashboard.urls")),
    path("queue/", include("apps.moderation.queue.urls")),
    path("decision/", include("apps.moderation.decision_row.urls")),
    # login later:
    # path("login/", include("apps.moderation.login.urls")),
]
