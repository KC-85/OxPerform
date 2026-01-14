from django.conf import settings
from django.db import models
from django.utils import timezone

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Region(models.TextChoices):
    OXFORD = "oxford", "Oxford"
    WEST_OXON = "westoxon", "West Oxfordshire"
    EAST_OXON = "eastoxon", "East Oxfordshire"
    NORTH_OXON = "northoxon", "North Oxfordshire"
    SOUTH_OXON = "southoxon", "South Oxfordshire"

class ModerationAction(models.TextChoices):
    APPROVE = "approve", "Approve"
    REJECT = "reject", "Reject"
    CANCEL = "cancel", "Cancel"
    UNCANCEL = "uncancel", "Un-cancel"
    FEATURE = "feature", "Feature"
    UNFEATURE = "unfeature", "Un-feature"
    HIDE = "hide", "Hide (make not public)"
    UNHIDE = "unhide", "Un-hide (make public)"

class EventModerationLog(TimeStampedModel):
    """
    Audit trail for moderation actions.

    We reference an event by (region, event_id) because each region has its own Event model/table.
    """
    region = models.CharField(max_length=20, choices=Region.choices)
    event_id = models.PositiveIntegerField()

    action = models.CharField(max_length=20, choices=ModerationAction.choices)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderation_actions",
    )

    note = models.TextField(blank=True)

    # Useful to snapshot "what happened" time explicitly (also equals created_at, but clearer)
    acted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-acted_at"]
        indexes = [
            models.Index(fields=["region", "event_id"]),
            models.Index(fields=["action", "acted_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.region}:{self.event_id} {self.action}"
