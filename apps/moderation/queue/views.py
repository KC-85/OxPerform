from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import QuerySet
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from apps.moderation.models import EventModerationLog, Region

# Import region models (each region is its own app/table)
from apps.events.oxford.models import Event as OxfordEvent, EventStatus as OxfordStatus
from apps.events.oxfordshire.west.models import Event as WestEvent, EventStatus as WestStatus
from apps.events.oxfordshire.east.models import Event as EastEvent, EventStatus as EastStatus
from apps.events.oxfordshire.north.models import Event as NorthEvent, EventStatus as NorthStatus
from apps.events.oxfordshire.south.models import Event as SouthEvent, EventStatus as SouthStatus

@dataclass(frozen=True)
class RegionSpec:
    key: str
    label: str
    EventModel: type
    Status: type

REGIONS: dict[str, RegionSpec] = {
    Region.OXFORD: RegionSpec(Region.OXFORD, "Oxford", OxfordEvent, OxfordStatus),
    Region.WEST_OXON: RegionSpec(Region.WEST_OXON, "West Oxfordshire", WestEvent, WestStatus),
    Region.EAST_OXON: RegionSpec(Region.EAST_OXON, "East Oxfordshire", EastEvent, EastStatus),
    Region.NORTH_OXON: RegionSpec(Region.NORTH_OXON, "North Oxfordshire", NorthEvent, NorthStatus),
    Region.SOUTH_OXON: RegionSpec(Region.SOUTH_OXON, "South Oxfordshire", SouthEvent, SouthStatus),
}

def _parse_region(region: Optional[str]) -> Optional[RegionSpec]:
    if not region:
        return None
    spec = REGIONS.get(region)
    if not spec:
        raise Http404("Unknown region")
    return spec

def _pending_events_qs(spec: RegionSpec) -> QuerySet:
    """
    Pending items for moderation.
    We don't show non-public or cancelled stuff here unless I later want that.
    """
    return (
        spec.EventModel.objects.select_related("venue")
        .filter(status=spec.Status.PENDING)
        .order_by("start_at")
    )


def _apply_filters(qs: QuerySet, q: str | None, category: str | None) -> QuerySet:
    if q:
        # Title/venue name search
        qs = qs.filter(title__icontains=q) | qs.filter(venue__name__icontains=q)
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

    selected_spec = _parse_region(region_key)

    items: list[dict] = []
    total = 0

    specs = [selected_spec] if selected_spec else list(REGIONS.values())

    for spec in specs:
        qs = _pending_events_qs(spec)
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
                    "region": spec.key,
                    "region_label": spec.label,
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
        "regions": [(k, v.label) for k, v in REGIONS.items()],
        "selected_region": region_key or "",
        "q": q or "",
        "category": category or "",
        "recent_logs": recent_logs,
        "now": timezone.now(),
    }
    return render
        (request, "moderation/queue/home.html", context)
