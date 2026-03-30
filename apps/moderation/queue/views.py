from __future__ import annotations

from typing import Optional

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import QuerySet
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from apps.moderation.models import EventModerationLog, Region
from apps.events.models import Event, EventStatus

REGIONS: dict[str, str] = {
    Region.OXFORD: "Oxford",
    Region.WEST_OXON: "West Oxfordshire",
    Region.EAST_OXON: "East Oxfordshire",
    Region.NORTH_OXON: "North Oxfordshire",
    Region.SOUTH_OXON: "South Oxfordshire",
}

def _parse_region(region: Optional[str]) -> Optional[str]:
    if not region:
        return None
    if region not in REGIONS:
        raise Http404("Unknown region")
    return region

def _pending_events_qs(region_key: str) -> QuerySet:
    """
    Pending items for moderation.
    We don't show non-public or cancelled stuff here unless I later want that.
    """
    return (
        Event.objects.select_related("venue")
        .filter(region=region_key, status=EventStatus.PENDING)
        .order_by("start_at")
    )


def _apply_filters(qs: QuerySet, q: str | None, category: str | None) -> QuerySet:
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(venue__name__icontains=q))
    if category:
        qs = qs.filter(category=category)
    return qs

@staff_member_required
def queue_home(request):
    """
    Queue landing: shows pending events for moderation across all regions,
    with optional filtering.
    """

    # e.g. "oxford", "westoxon"
    region_key = request.GET.get("region")
    q = (request.GET.get("q") or "").strip() or None
    category = (request.GET.get("category") or "").strip() or None

    selected_region = _parse_region(region_key)

    items: list[dict] = []
    total = 0

    region_keys = [selected_region] if selected_region else list(REGIONS.keys())

    for key in region_keys:
        qs = _pending_events_qs(key)
        qs = _apply_filters(qs, q, category)

        # Optional: hide events that already have recent moderation logs
        # (comment out if i want everything)
        # Example: if i log APPROVE/REJECT, i can exclude those IDs here.

        count = qs.count()
        total += count

        # safety limit for now
        for e in qs[:200]:
            items.append(
                {
                    "region": key,
                    "region_label": REGIONS[key],
                    "id": e.id,
                    "slug": getattr(e, "slug", ""),
                    "title": e.title,
                    "start_at": e.start_at,
                    "venue_name": getattr(e.venue, "name", ""),
                    "category": getattr(e, "category", ""),
                    "is_public": getattr(e, "is_public", True),
                }
            )

    # Sort combined list by start time (soonest first)
    items.sort(key=lambda x: (x["start_at"] or timezone.now()))

    # Recent moderation actions (useful sidebar)
    recent_logs = EventModerationLog.objects.select_related("actor").all()[:20]

    context = {
        "items": items,
        "total": total,
        "regions": [(k, label) for k, label in REGIONS.items()],
        "selected_region": region_key or "",
        "q": q or "",
        "category": category or "",
        "recent_logs": recent_logs,
        "now": timezone.now(),
    }
    return render(request, "moderation/queue/home.html", context)
