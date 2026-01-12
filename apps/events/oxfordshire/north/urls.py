from django.urls import path

from . import views

app_name = "northoxon"

urlpatterns = [
    # Events
    path("", views.upcoming_events, name="upcoming_events"),
    path("past/", views.past_events, name="past_events"),
    path("category/<slug:category>/", views.category_events, name="category_events"),

    # Venues
    path("venues/", views.venue_list, name="venue_list"),
    path("venues/<int:pk>/", views.venue_detail, name="venue_detail"),

    # Event Detail
    path("<slug:slug>/", views.event_detail, name="event_detail"),
]
