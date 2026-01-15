from django.urls import path
from . import views

app_name = "decision_row"

urlpatterns = [
    # /moderation/decision/
    path("", views.decision_home, name="home"),

    # /moderation/decision/<region>/<int:event_id>/
    path("<slug:region>/<int:event_id>/", views.decision_home, name="row"),

    # Actions (POST targets)
    # /moderation/decision/<region>/<int:event_id>/approve/
    path("<slug:region>/<int:event_id>/approve/", views.approve_event, name="approve"),
    path("<slug:region>/<int:event_id>/reject/", views.reject_event, name="reject"),
    path("<slug:region>/<int:event_id>/cancel/", views.cancel_event, name="cancel"),
    path("<slug:region>/<int:event_id>/uncancel/", views.uncancel_event, name="uncancel"),
    path("<slug:region>/<int:event_id>/feature/", views.feature_event, name="feature"),
    path("<slug:region>/<int:event_id>/unfeature/", views.unfeature_event, name="unfeature"),
    path("<slug:region>/<int:event_id>/hide/", views.hide_event, name="hide"),
    path("<slug:region>/<int:event_id>/unhide/", views.unhide_event, name="unhide"),
]
