from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.events.oxfordshire.north.models import Event, EventStatus, Venue


User = get_user_model()


class SouthOxonModelsTests(TestCase):
    def test_venue_slug_autogenerates(self):
        v = Venue.objects.create(name="The Blue Bell")
        self.assertTrue(v.slug)

    def test_event_slug_autogenerates(self):
        v = Venue.objects.create(name="Venue One")
        e = Event.objects.create(
            title="My Event Title",
            venue=v,
            category="other",
            start_at=timezone.now(),
            status=EventStatus.APPROVED,
            is_public=True,
        )
        self.assertTrue(e.slug)

    def test_event_approve_sets_fields(self):
        reviewer = User.objects.create_user(username="reviewer", password="pass")
        v = Venue.objects.create(name="Venue Two")
        e = Event.objects.create(
            title="Needs Approval",
            venue=v,
            category="music",
            start_at=timezone.now(),
        )

        e.approve(reviewer, note="Looks good")
        e.refresh_from_db()

        self.assertEqual(e.status, EventStatus.APPROVED)
        self.assertEqual(e.reviewed_by, reviewer)
        self.assertIsNotNone(e.reviewed_at)
        self.assertEqual(e.review_note, "Looks good")

    def test_event_reject_sets_fields(self):
        reviewer = User.objects.create_user(username="reviewer2", password="pass")
        v = Venue.objects.create(name="Venue Three")
        e = Event.objects.create(
            title="Bad Event",
            venue=v,
            category="music",
            start_at=timezone.now(),
        )

        e.reject(reviewer, note="Not suitable")
        e.refresh_from_db()

        self.assertEqual(e.status, EventStatus.REJECTED)
        self.assertEqual(e.reviewed_by, reviewer)
        self.assertIsNotNone(e.reviewed_at)
        self.assertEqual(e.review_note, "Not suitable")
