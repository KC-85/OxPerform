from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.events.oxford.models import Event, EventStatus, EventCategory, Venue

class OxfordViewsTestCase(TestCase):
    def setUp(self):
        self.venue_active = Venue.objects.create(name="The Bull", is_active=True)
        self.venue_inactive = Venue.objects.create(name="Closed Venue", is_active=False)

        now = timezone.now()

        # Approved + public + active venue + upcoming (should show)
        self.event_upcoming_ok = Event.objects.create(
            title="Open Mic Night",
            venue=self.venue_active,
            category=EventCategory.OPEN_MIC,
            start_at=now + timedelta(days=3),
            end_at=now + timedelta(days=3, hours=2),
            status=EventStatus.APPROVED,
            is_public=True,
        )

        # Approved + public + active venue + past (should show in past)
        self.event_past_ok = Event.objects.create(
            title="Past Comedy",
            venue=self.venue_active,
            category=EventCategory.COMEDY,
            start_at=now - timedelta(days=5),
            end_at=now - timedelta(days=5, hours=-2),
            status=EventStatus.APPROVED,
            is_public=True,
        )

        # Pending (should NOT show publicly)
        self.event_pending = Event.objects.create(
            title="Pending Event",
            venue=self.venue_active,
            category=EventCategory.MUSIC,
            start_at=now + timedelta(days=1),
            end_at=now + timedelta(days=1, hours=2),
            status=EventStatus.PENDING,
            is_public=True,
        )

        # Not public (should NOT show)
        self.event_private = Event.objects.create(
            title="Hidden Event",
            venue=self.venue_active,
            category=EventCategory.MUSIC,
            start_at=now + timedelta(days=2),
            end_at=now + timedelta(days=2, hours=2),
            status=EventStatus.APPROVED,
            is_public=False,
        )

        # Venue inactive (should NOT show)
        self.event_inactive_venue = Event.objects.create(
            title="Inactive Venue Event",
            venue=self.venue_inactive,
            category=EventCategory.MUSIC,
            start_at=now + timedelta(days=2),
            end_at=now + timedelta(days=2, hours=2),
            status=EventStatus.APPROVED,
            is_public=True,
        )

    def test_upcoming_events_list_shows_only_approved_public_active_venue_upcoming(self):
        url = reverse('oxford:upcoming_events')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        events = resp.context['events']
        self.assertIn(self.event_upcoming_ok, events)

        self.assertNotIn(self.event_past_ok, events)
        self.assertNotIn(self.event_pending, events)
        self.assertNotIn(self.event_private, events)
        self.assertNotIn(self.event_inactive_venue, events)

        def test_past_events_list_shows_only_past_approved_public_active_venue(self):
            url = reverse("oxford:past_events")
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)

            events = list(resp.context["events"])
            self.assertIn(self.event_past_ok, events)

            self.assertNotIn(self.event_upcoming_ok, events)
            self.assertNotIn(self.event_pending, events)
            self.assertNotIn(self.event_private, events)
            self.assertNotIn(self.event_inactive_venue, events)

    def test_category_view_filters_by_category(self):
        url = reverse("oxford:category_events", kwargs={"category": "open_mic"})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        events = list(resp.context["events"])
        self.assertIn(self.event_upcoming_ok, events)
        self.assertNotIn(self.event_past_ok, events)

        print("event category:", self.event_upcoming_ok.category)
        print("url:", url)


    def test_event_detail_200_for_approved_public_active_venue(self):
        url = reverse("oxford:event_detail", kwargs={"slug": self.event_upcoming_ok.slug})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.event_upcoming_ok.title)

    def test_event_detail_404_for_pending(self):
        url = reverse("oxford:event_detail", kwargs={"slug": self.event_pending.slug})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_event_detail_404_for_not_public(self):
        url = reverse("oxford:event_detail", kwargs={"slug": self.event_private.slug})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_event_detail_404_for_inactive_venue(self):
        url = reverse("oxford:event_detail", kwargs={"slug": self.event_inactive_venue.slug})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)
