from __future__ import annotations

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import ModerationDecisionForm
from .models import EventModerationLog, ModerationAction, Region
from apps.events.models import Event, EventStatus


REGION_LABELS: dict[str, str] = {
    Region.OXFORD: "Oxford",
    Region.WEST_OXON: "West Oxfordshire",
    Region.EAST_OXON: "East Oxfordshire",
    Region.NORTH_OXON: "North Oxfordshire",
    Region.SOUTH_OXON: "South Oxfordshire",
}


def _get_event(region: str, event_id: int):
    if region not in REGION_LABELS:
        raise Http404("Unknown region")
    return get_object_or_404(Event.objects.select_related("venue"), region=region, pk=event_id)


def _apply_action(event, action: str, note: str) -> None:
    """
    Mutate the event based on action. Keep this small + explicit.
    """
    now = timezone.now()

    if action == ModerationAction.APPROVE:
        event.status = EventStatus.APPROVED

    elif action == ModerationAction.REJECT:
        event.status = EventStatus.REJECTED
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
        event.status = EventStatus.CANCELLED

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
        return {
            "pending": Event.objects.filter(region=region_key, status=EventStatus.PENDING).count(),
            "approved_upcoming": Event.objects.filter(
                region=region_key,
                status=EventStatus.APPROVED,
                start_at__gte=now,
            ).count(),
            "cancelled": Event.objects.filter(region=region_key, is_cancelled=True).count(),
        }

    stats = {key: stats_for(key) for key in REGION_LABELS.keys()}

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

            event = _get_event(region, event_id)

            try:
                _apply_action(event, action, note)
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

    for region_key, region_label in REGION_LABELS.items():
        qs = (
            Event.objects.select_related("venue")
            .filter(
                region=region_key,
                status=EventStatus.PENDING,
                venue__is_active=True,
            )
            .order_by("start_at")
        )
        for ev in qs:
            queue_items.append(
                {
                    "region": region_key,
                    "region_label": region_label,
                    "event": ev,
                    "starts_in_past": ev.start_at < now,
                }
            )

    # Sort across all regions by start date
    queue_items.sort(key=lambda x: x["event"].start_at)

    return render(
        request,
        "moderation/home.html",
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
