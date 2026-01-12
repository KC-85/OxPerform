from django import forms
from django.utils import timezone

from .models import Event, Venue

class VenueForm(forms.ModelForm):
    """Internal (staff-only) form for creating/editing Venues."""

    class Meta:
        model = Venue
        fields = [
            "name",
            "address_line_1",
            "address_line_2",
            "town",
            "postcode",
            "website",
            "contact_email",
            "phone",
            "is_active",
        ]

class EventForm(forms.ModelForm):
    """Internal (staff-only) form for creating/editing Events."""

    class Meta:
        model = Event
        fields = [
            "title",
            "venue",
            "category",
            "start_at",
            "end_at",
            "description",
            "is_public",
            "is_featured",

            # lifecycle
            "is_cancelled",
            "cancelled_at",
            "cancellation_note",
        ]
        widgets = {
            "start_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "cancelled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 6}),
            "cancellation_note": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()

        start_at = cleaned.get("start_at")
        end_at = cleaned.get("end_at")

        is_cancelled = cleaned.get("is_cancelled")
        cancelled_at = cleaned.get("cancelled_at")

        # time sanity
        if start_at and end_at and end_at <= start_at:
            self.add_error("end_at", "End time must be after the start time.")

        # cancellation sanity
        if is_cancelled:
            if not cancelled_at:
                cleaned["cancelled_at"] = timezone.now()
        else:
            cleaned["cancelled_at"] = None
            cleaned["cancellation_note"] = ""

        return cleaned
