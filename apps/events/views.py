from datetime import timedelta

from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Event, EventCategory, EventRegion, EventStatus, Venue


NAMESPACE_TO_REGION = {
    "oxford": EventRegion.OXFORD,
    "westoxon": EventRegion.WEST_OXON,
    "eastoxon": EventRegion.EAST_OXON,
    "northoxon": EventRegion.NORTH_OXON,
    "southoxon": EventRegion.SOUTH_OXON,
}

NAMESPACE_TO_TEMPLATE_PREFIX = {
    "oxford": "events/oxford",
    "westoxon": "events/oxfordshire/west",
    "eastoxon": "events/oxfordshire/east",
    "northoxon": "events/oxfordshire/north",
    "southoxon": "events/oxfordshire/south",
}


def _active_region(request) -> str:
    namespace = request.resolver_match.namespace if request.resolver_match else None
    region = NAMESPACE_TO_REGION.get(namespace or "")
    if not region:
        raise Http404("Unknown event region")
    return region


def _template_prefix(request) -> str:
    namespace = request.resolver_match.namespace if request.resolver_match else None
    prefix = NAMESPACE_TO_TEMPLATE_PREFIX.get(namespace or "")
    if not prefix:
        raise Http404("Unknown event region")
    return prefix


def upcoming_events(request):
    now = timezone.now()
    region = _active_region(request)

    events = (
        Event.objects.select_related("venue")
        .filter(
            region=region,
            status=EventStatus.APPROVED,
            is_public=True,
            venue__is_active=True,
            start_at__gte=now,
        )
        .order_by("start_at")
    )

    return render(request, f"{_template_prefix(request)}/upcoming_events.html", {"events": events, "now": now})


def event_detail(request, slug: str):
    region = _active_region(request)

    event = get_object_or_404(
        Event.objects.select_related("venue"),
        region=region,
        slug=slug,
        status=EventStatus.APPROVED,
        is_public=True,
        venue__is_active=True,
    )

    return render(request, f"{_template_prefix(request)}/event_detail.html", {"event": event, "now": timezone.now()})


def venue_list(request):
    region = _active_region(request)

    venues = Venue.objects.filter(is_active=True, events__region=region).distinct().order_by("name")

    return render(request, f"{_template_prefix(request)}/venue_list.html", {"venues": venues})


def venue_detail(request, pk: int):
    region = _active_region(request)
    venue = get_object_or_404(Venue, pk=pk, is_active=True)

    upcoming = (
        Event.objects.filter(
            region=region,
            venue=venue,
            status=EventStatus.APPROVED,
            is_public=True,
            start_at__gte=timezone.now(),
        )
        .order_by("start_at")
    )

    return render(
        request,
        f"{_template_prefix(request)}/venue_detail.html",
        {"venue": venue, "upcoming_events": upcoming, "now": timezone.now()},
    )


def category_events(request, category: str):
    valid_values = {c.value for c in EventCategory}
    if category not in valid_values:
        raise Http404()

    now = timezone.now()
    region = _active_region(request)

    events = (
        Event.objects.select_related("venue")
        .filter(
            region=region,
            category=category,
            status=EventStatus.APPROVED,
            is_public=True,
            venue__is_active=True,
            start_at__gte=now - timedelta(minutes=1),
        )
        .order_by("start_at")
    )

    return render(
        request,
        f"{_template_prefix(request)}/category_events.html",
        {"events": events, "category": category, "now": now},
    )


def past_events(request):
    now = timezone.now()
    region = _active_region(request)

    events = (
        Event.objects.select_related("venue")
        .filter(
            region=region,
            status=EventStatus.APPROVED,
            is_public=True,
            venue__is_active=True,
            start_at__lt=now,
        )
        .order_by("-start_at")
    )

    return render(request, f"{_template_prefix(request)}/past_events.html", {"events": events, "now": now})