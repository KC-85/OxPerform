"""
These are views for the Oxfordshire West events app.
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

from .models import Event, EventStatus, EventCategory
from .models import Venue


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
        "events/oxfordshire/west/upcoming_events.html",
        {
            "events": events,
            "now": now,
        },
    )

def event_detail(request, slug: str):
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
        "events/oxfordshire/west/event_detail.html",
        {
            "event": event,
            "now": timezone.now(),
        },
    )

def venue_list(request):
    """
    List all active venues for Oxford events.
    """
    venues = Venue.objects.filter(is_active=True).order_by("name")

    return render(
        request,
        "events/oxfordshire/west/venue_list.html",
        {
            "venues": venues,
        },
    )

def venue_detail(request, pk: int):
    """
    Display the details of a specific venue.
    """
    venue = get_object_or_404(Venue, pk=pk, is_active=True)

    upcoming_events = (
        Event.objects.filter(
            venue=venue,
            status=EventStatus.APPROVED,
            is_public=True,
            start_at__gte=timezone.now(),
        )
        .order_by("start_at")
    )

    return render(
        request,
        "events/oxfordshire/west/venue_detail.html",
        {
            "venue": venue,
            "upcoming_events": upcoming_events,
            "now": timezone.now(),
        },
    )

def category_events(request, category: str):
    """
    List upcoming Oxford events in a specific category.

    `category` must be one of EventCategory values (e.g. "music", "comedy").
    """

    # Validate category against allowed choices
    valid_values = {c.value for c in EventCategory}
    if category not in valid_values:
        raise Http404()

    now = timezone.now()

    events = (
        Event.objects.select_related("venue")
        .filter(
            category=category,
            status=EventStatus.APPROVED,
            is_public=True,
            venue__is_active=True,
            start_at__gte=now - timezone.timedelta(minutes=1),
        )
        .order_by("start_at")
    )

    return render(
        request,
        "events/oxfordshire/west/category_events.html",
        {
            "events": events,
            "category": category,
            "now": now,
        },
    )

def past_events(request):
    """
    List past, public, approved Oxford events.

    Filters:
    - approved events only
    - public events only
    - venue must be active
    - start time before now
    """
    now = timezone.now()

    events = (
        Event.objects.select_related("venue")
        .filter(
            status=EventStatus.APPROVED,
            is_public=True,
            venue__is_active=True,
            start_at__lt=now,
        )
        .order_by("-start_at")
    )

    return render(
        request,
        "events/oxfordshire/west/past_events.html",
        {
            "events": events,
            "now": now,
        },
    )
