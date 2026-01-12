from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Venue(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    town = models.CharField(max_length=120, blank=True)
    postcode = models.CharField(max_length=12, blank=True)

    website = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["town"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:240] or "venue"
            slug = base
            i = 2
            while Venue.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class EventCategory(models.TextChoices):
    MUSIC = "music", "Music"
    COMEDY = "comedy", "Comedy"
    OPEN_MIC = "open_mic", "Open mic"
    THEATRE = "theatre", "Theatre"
    COMMUNITY = "community", "Community"
    OTHER = "other", "Other"


class EventStatus(models.TextChoices):
    PENDING = "pending", "Pending approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class Event(TimeStampedModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="events")
    category = models.CharField(max_length=30, choices=EventCategory.choices, default=EventCategory.OTHER)

    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_note = models.CharField(max_length=500, blank=True)

    description = models.TextField(blank=True)

    # Ticket/pricing (keep flexible early)
    is_free = models.BooleanField(default=False)
    price_text = models.CharField(max_length=100, blank=True)
    ticket_url = models.URLField(blank=True)

    # Moderation for pilot/public facing
    status = models.CharField(max_length=20, choices=EventStatus.choices, default=EventStatus.PENDING)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="southoxon_submitted_events",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="southoxon_reviewed_events",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    is_featured = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ["-start_at"]
        indexes = [
            models.Index(fields=["status", "start_at"]),
            models.Index(fields=["venue", "start_at"]),
            models.Index(fields=["slug"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:240] or "event"
            slug = base
            i = 2
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_upcoming(self) -> bool:
        return self.start_at >= timezone.now()

    def approve(self, reviewer, note: str = ""):
        self.status = EventStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_note = note
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "updated_at"])

    def reject(self, reviewer, note: str):
        self.status = EventStatus.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.reviewed_at = timezone.now()
        self.review_note = note
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "updated_at"])

    def __str__(self) -> str:
        return self.title
