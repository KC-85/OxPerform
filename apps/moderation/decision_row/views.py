from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.moderation.models import EventModerationLog, Region, ModerationAction


@dataclass(frozen=True)
class RegionBinding:
    Event: Type
    EventStatus: Type


def _get_region_binding(region: str) -> RegionBinding:
    """
    Maps a region slug to its Event model + EventStatus enum.
    Keep this in ONE place so the rest of your moderation stays clean.
    """
    if region == Region.OXFORD:
        from apps.events.oxford.models import Event, EventStatus
        return RegionBinding(Event=Event, EventStatus=EventStatus)

    if region == Region.WEST_OXON:
        from apps.events.oxfordshire.west.models import Event, EventStatus
        return RegionBinding(Event=Event, EventStatus=EventStatus)

    if region == Region.EAST_OXON:
        from apps.events.oxfordshire.east.models import Event, EventStatus
        return RegionBinding(Event=Event, EventStatus=EventStatus)

    if region == Region.NORTH_OXON:
        from apps.events.oxfordshire.north.models import Event, EventStatus
        return RegionBinding(Event=Event, EventStatus=EventStatus)

    if region == Region.SOUTH_OXON:
        from apps.events.oxfordshire.south.models import Event, EventStatus
        return RegionBinding(Event=Event, EventStatus=EventStatus)

    raise Http404("Unknown region")


def _require_post(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    return None


def _get_next_url(request) -> str:
    """
    Allows buttons to send you back where you came from.
    """
    return request.POST.get("next") or request.GET.get("next") or "moderation:home"


def _log_action(*, region: str, event_id: int, action: str, actor, note: str = "") -> None:
    EventModerationLog.objects.create(
        region=region,
        event_id=event_id,
        action=action,
        actor=actor,
        note=note or "",
        acted_at=timezone.now(),
    )


def _set_event_fields(event, **fields):
    """
    Small helper: set fields and save with update_fields.
    Assumes event has updated_at from TimeStampedModel.
    """
    for k, v in fields.items():
        setattr(event, k, v)

    update_fields = list(fields.keys())
    if hasattr(event, "updated_at"):
        update_fields.append("updated_at")

    event.save(update_fields=update_fields)


@staff_member_required
def decision_home(request):
    # Keep this minimal for now (template skeleton is fine)
    return render(request, "moderation/decision_row/home.html")


@staff_member_required
def approve_event(request, region: str, event_id: int):
    not_allowed = _require_post(request)
    if not_allowed:
        return not_allowed

    binding = _get_region_binding(region)
    event = get_object_or_404(binding.Event, pk=event_id)

    _set_event_fields(
        event,
        status=binding.EventStatus.APPROVED,
        reviewed_by=request.user if hasattr(event, "reviewed_by") else None,
        reviewed_at=timezone.now() if hasattr(event, "reviewed_at") else None,
        review_note=request.POST.get("note", "") if hasattr(event, "review_note") else "",
    )

    _log_action(region=region, event_id=event_id, action=ModerationAction.APPROVE, actor=request.user, note=request.POST.get("note", ""))
    messages.success(request, "Approved event.")
    return redirect(_get_next_url(request))


@staff_member_required
def reject_event(request, region: str, event_id: int):
    not_allowed = _require_post(request)
    if not_allowed:
        return not_allowed

    binding = _get_region_binding(region)
    event = get_object_or_404(binding.Event, pk=event_id)

    note = request.POST.get("note", "")
    if not note:
        messages.error(request, "Rejection requires a note.")
        return redirect(_get_next_url(request))

    _set_event_fields(
        event,
        status=binding.EventStatus.REJECTED,
        reviewed_by=request.user if hasattr(event, "reviewed_by") else None,
        reviewed_at=timezone.now() if hasattr(event, "reviewed_at") else None,
        review_note=note if hasattr(event, "review_note") else "",
    )

    _log_action(region=region, event_id=event_id, action=ModerationAction.REJECT, actor=request.user, note=note)
    messages.success(request, "Rejected event.")
    return redirect(_get_next_url(request))


@staff_member_required
def cancel_event(request, region: str, event_id: int):
    not_allowed = _require_post(request)
    if not_allowed:
        return not_allowed

    binding = _get_region_binding(region)
    event = get_object_or_404(binding.Event, pk=event_id)

    note = request.POST.get("note", "")

    # Your Event model has is_cancelled/cancelled_at/cancellation_note
    _set_event_fields(
        event,
        status=binding.EventStatus.CANCELLED if hasattr(binding.EventStatus, "CANCELLED") else event.status,
        is_cancelled=True,
        cancelled_at=timezone.now(),
        cancellation_note=note,
    )

    _log_action(region=region, event_id=event_id, action=ModerationAction.CANCEL, actor=request.user, note=note)
    messages.success(request, "Cancelled event.")
    return redirect(_get_next_url(request))


@staff_member_required
def uncancel_event(request, region: str, event_id: int):
    not_allowed = _require_post(request)
    if not_allowed:
        return not_allowed

    binding = _get_region_binding(region)
    event = get_object_or_404(binding.Event, pk=event_id)

    # On uncancel, return to approved (pilot assumption)
    _set_event_fields(
        event,
        status=binding.EventStatus.APPROVED,
        is_cancelled=False,
        cancelled_at=None,
        cancellation_note="",
    )

    _log_action(region=region, event_id=event_id, action=ModerationAction.UNCANCEL, actor=request.user)
    messages.success(request, "Un-cancelled event.")
    return redirect(_get_next_url(request))


@staff_member_required
def feature_event(request, region: str, event_id: int):
    not_allowed = _require_post(request)
    if not_allowed:
        return not_allowed

    binding = _get_region_binding(region)
    event = get_object_or_404(binding.Event, pk=event_id)

    _set_event_fields(event, is_featured=True)

    _log_action(region=region, event_id=event_id, action=ModerationAction.FEATURE, actor=request.user)
    messages.success(request, "Featured event.")
    return redirect(_get_next_url(request))


@staff_member_required
def unfeature_event(request, region: str, event_id: int):
    not_allowed = _require_post(request)
    if not_allowed:
        return not_allowed

    binding = _get_region_binding(region)
    event = get_object_or_404(binding.Event, pk=event_id)

    _set_event_fields(event, is_featured=False)

    _log_action(region=region, event_id=event_id, action=ModerationAction.UNFEATURE, actor=request.user)
    messages.success(request, "Un-featured event.")
    return redirect(_get_next_url(request))


@staff_member_required
def hide_event(request, region: str, event_id: int):
    not_allowed = _require_post(request)
    if not_allowed:
        return not_allowed

    binding = _get_region_binding(region)
    event = get_object_or_404(binding.Event, pk=event_id)

    _set_event_fields(event, is_public=False)

    _log_action(region=region, event_id=event_id, action=ModerationAction.HIDE, actor=request.user)
    messages.success(request, "Event hidden (not public).")
    return redirect(_get_next_url(request))


@staff_member_required
def unhide_event(request, region: str, event_id: int):
    not_allowed = _require_post(request)
    if not_allowed:
        return not_allowed

    binding = _get_region_binding(region)
    event = get_object_or_404(binding.Event, pk=event_id)

    _set_event_fields(event, is_public=True)

    _log_action(region=region, event_id=event_id, action=ModerationAction.UNHIDE, actor=request.user)
    messages.success(request, "Event is public again.")
    return redirect(_get_next_url(request))
