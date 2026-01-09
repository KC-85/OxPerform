"""
These are views for the Oxford events app.
They handle the display and management of events specific to Oxford.
They extend the base event views to provide customised functionality
These will be passed through the URL routing system to the Template,
as per Django's MVT architecture.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Avg
from django.shortcuts import render
from django.utils import timezone

from .models import Event, EventStatus


def upcoming_events(request):
    """
    List upcoming, public, approved Oxford events.

    Filters:
    - approved events only
    - public events only
    - venue must be active
    - start time from now onwards
    """
    now = timezone.now()

    events = (
        Event.objects.select_related("venue")
        .filter(
            status=EventStatus.APPROVED,
            is_public=True,
            venue__is_active=True,
            start_at__gte=now,
        )
        .order_by("start_at")
    )

    return render(
        request,
        "events/oxford/upcoming_events.html",
        {
            "events": events,
            "now": now,
        },
    )

def event_detail(request, slug: str)
    """
    Display the details of a specific Oxford event.

    Args:
        slug (str): The slug of the event to display.
    """
    event = get_object_or_404(
        Event.objects.select_related("venue"),
        slug=slug,
        status=EventStatus.APPROVED,
        is_public=True,
        venue__is_active=True,
    )

    return render(
        request,
        "events/oxford/event_detail.html",
        {
            "event": event,
            "now": timezone.now(),
        },
    )