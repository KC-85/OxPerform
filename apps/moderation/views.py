from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Type

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import ModerationDecisionForm
from .models import EventModerationLog, ModerationAction, Region

# Import each region's Event + EventStatus
from apps.events.oxford.models import Event as OxfordEvent, EventStatus as OxfordStatus
from apps.events.oxfordshire.west.models import Event as WestEvent, EventStatus as WestStatus
from apps.events.oxfordshire.east.models import Event as EastEvent, EventStatus as EastStatus
from apps.events.oxfordshire.north.models import Event as NorthEvent, EventStatus as NorthStatus
from apps.events.oxfordshire.south.models import Event as SouthEvent, EventStatus as SouthStatus


@dataclass(frozen=True)
class RegionModelConfig:
    event_model: Type[Any]
    status_enum: Type[Any]


REGION_CONFIG: dict[str, RegionModelConfig] = {
    Region.OXFORD: RegionModelConfig(event_model=OxfordEvent, status_enum=OxfordStatus),
    Region.WEST_OXON: RegionModelConfig(event_model=WestEvent, status_enum=WestStatus),
    Region.EAST_OXON: RegionModelConfig(event_model=EastEvent, status_enum=EastStatus),
    Region.NORTH_OXON: RegionModelConfig(event_model=NorthEvent, status_enum=NorthStatus),
    Region.SOUTH_OXON: RegionModelConfig(event_model=SouthEvent, status_enum=SouthStatus),
}


def _get_event(region: str, event_id: int):
    cfg = REGION_CONFIG.get(region)
    if not cfg:
        raise Http404("Unknown region")
    try:
        return cfg.event_model.objects.select_related("venue").get(pk=event_id)
    except cfg.event_model.DoesNotExist:
        raise Http404("Event not found")


def _apply_action(event, status_enum, action: str, note: str) -> None:
    """
    Mutate the event based on action. Keep this small + explicit.
    """
    now = timezone.now()

    if action == ModerationAction.APPROVE:
        event.status = status_enum.APPROVED

    elif action == ModerationAction.REJECT:
        event.status = status_enum.REJECTED
        # Keep your existing review_note field usage
        if hasattr(event, "review_note"):
            event.review_note = note

    elif action == ModerationAction.CANCEL:
        # Public-facing lifecycle cancellation
        if hasattr(event, "is_cancelled"):
            event.is_cancelled = True
        if hasattr(event, "cancelled_at"):
            event.cancelled_at = now
        if hasattr(event, "cancellation_note"):
            event.cancellation_note = note
        # Optional: also set status to CANCELLED if you want that semantic
        # event.status = status_enum.CANCELLED

    elif action == ModerationAction.UNCANCEL:
        if hasattr(event, "is_cancelled"):
            event.is_cancelled = False
        if hasattr(event, "cancelled_at"):
            event.cancelled_at = None
        if hasattr(event, "cancellation_note"):
            event.cancellation_note = ""

    elif action == ModerationAction.FEATURE:
        if hasattr(event, "is_featured"):
            event.is_featured = True

    elif action == ModerationAction.UNFEATURE:
        if hasattr(event, "is_featured"):
            event.is_featured = False

    elif action == ModerationAction.HIDE:
        if hasattr(event, "is_public"):
            event.is_public = False

    elif action == ModerationAction.UNHIDE:
        if hasattr(event, "is_public"):
            event.is_public = True

    else:
        raise ValueError(f"Unknown action: {action}")

    event.save()


@staff_member_required
def moderation_home(request: HttpRequest) -> HttpResponse:
    """
    Simple landing page: counts + links to queue.
    Keep templates minimal for MVP.
    """
    now = timezone.now()

    def stats_for(region_key: str):
        cfg = REGION_CONFIG[region_key]

        cancelled_count = (
            cfg.event_model.objects.filter(is_cancelled=True).count()
            if hasattr(cfg.event_model, "is_cancelled")
            else 0
        )

        return {
            "pending": cfg.event_model.objects.filter(status=cfg.status_enum.PENDING).count(),
            "approved_upcoming": cfg.event_model.objects.filter(
                status=cfg.status_enum.APPROVED,
                start_at__gte=now,
            ).count(),
            "cancelled": cancelled_count,
        }

    stats = {key: stats_for(key) for key in REGION_CONFIG.keys()}

    return render(request, "moderation/home.html", {"stats": stats})

@staff_member_required
@require_http_methods(["GET", "POST"])
def moderation_queue(request: HttpRequest) -> HttpResponse:
    """
    Shows pending events across all regions, newest first.
    POST handles decisions via ModerationDecisionForm.
    """
    if request.method == "POST":
        form = ModerationDecisionForm(request.POST)
        if form.is_valid():
            region = form.cleaned_data["region"]
            event_id = form.cleaned_data["event_id"]
            action = form.cleaned_data["action"]
            note = (form.cleaned_data.get("note") or "").strip()

            cfg = REGION_CONFIG[region]
            event = _get_event(region, event_id)

            try:
                _apply_action(event, cfg.status_enum, action, note)
            except Exception as e:
                messages.error(request, f"Could not apply action: {e}")
                return redirect("moderation:queue")

            EventModerationLog.objects.create(
                region=region,
                event_id=event_id,
                action=action,
                actor=request.user if request.user.is_authenticated else None,
                note=note,
            )

            messages.success(request, f"Action '{action}' applied to event #{event_id} ({region}).")
            return redirect("moderation:queue")
    else:
        form = ModerationDecisionForm()

    # Build a combined queue: pending + public + active venue, per region.
    # (If you want staff to see private entries too, remove is_public filter.)
    queue_items = []
    now = timezone.now()

    for region_key, cfg in REGION_CONFIG.items():
        qs = (
            cfg.event_model.objects.select_related("venue")
            .filter(
                status=cfg.status_enum.PENDING,
                venue__is_active=True,
            )
            .order_by("start_at")
        )
        for ev in qs:
            queue_items.append(
                {
                    "region": region_key,
                    "event": ev,
                    "starts_in_past": ev.start_at < now,
                }
            )

    # Sort across all regions by start date
    queue_items.sort(key=lambda x: x["event"].start_at)

    return render(
        request,
        "moderation/queue.html",
        {
            "items": queue_items,
            "form": form,
        },
    )


@staff_member_required
def moderation_log(request: HttpRequest) -> HttpResponse:
    """
    Simple audit log page.
    """
    logs = EventModerationLog.objects.select_related("actor").all()[:250]
    return render(request, "moderation/log.html", {"logs": logs})
