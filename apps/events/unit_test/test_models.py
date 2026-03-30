from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.events.models import Event, EventRegion, EventStatus, Venue


User = get_user_model()


class EventsModelsTests(TestCase):
    def test_venue_slug_autogenerates(self):
        venue = Venue.objects.create(name="The Blue Bell")
        self.assertTrue(venue.slug)

    def test_event_slug_autogenerates(self):
        venue = Venue.objects.create(name="Venue One")
        event = Event.objects.create(
            region=EventRegion.OXFORD,
            title="My Event Title",
            venue=venue,
            category="other",
            start_at=timezone.now(),
            status=EventStatus.APPROVED,
            is_public=True,
        )
        self.assertTrue(event.slug)

    def test_event_approve_sets_fields(self):
        reviewer = User.objects.create_user(username="reviewer", password="pass")
        venue = Venue.objects.create(name="Venue Two")
        event = Event.objects.create(
            region=EventRegion.WEST_OXON,
            title="Needs Approval",
            venue=venue,
            category="music",
            start_at=timezone.now(),
        )

        event.approve(reviewer, note="Looks good")
        event.refresh_from_db()

        self.assertEqual(event.status, EventStatus.APPROVED)
        self.assertEqual(event.reviewed_by, reviewer)
        self.assertIsNotNone(event.reviewed_at)
        self.assertEqual(event.review_note, "Looks good")

    def test_event_reject_sets_fields(self):
        reviewer = User.objects.create_user(username="reviewer2", password="pass")
        venue = Venue.objects.create(name="Venue Three")
        event = Event.objects.create(
            region=EventRegion.SOUTH_OXON,
            title="Bad Event",
            venue=venue,
            category="music",
            start_at=timezone.now(),
        )

        event.reject(reviewer, note="Not suitable")
        event.refresh_from_db()

        self.assertEqual(event.status, EventStatus.REJECTED)
        self.assertEqual(event.reviewed_by, reviewer)
        self.assertIsNotNone(event.reviewed_at)
        self.assertEqual(event.review_note, "Not suitable")
