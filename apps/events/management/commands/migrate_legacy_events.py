from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.events.models import Event, EventRegion, EventStatus, Venue


@dataclass(frozen=True)
class LegacyRegionConfig:
    region: str
    label: str
    venue_table: str
    event_table: str


LEGACY_REGIONS = [
    LegacyRegionConfig(EventRegion.OXFORD, "Oxford", "oxfordcity_venue", "oxfordcity_event"),
    LegacyRegionConfig(EventRegion.WEST_OXON, "West Oxfordshire", "westoxon_venue", "westoxon_event"),
    LegacyRegionConfig(EventRegion.EAST_OXON, "East Oxfordshire", "eastoxon_venue", "eastoxon_event"),
    LegacyRegionConfig(EventRegion.NORTH_OXON, "North Oxfordshire", "northoxon_venue", "northoxon_event"),
    LegacyRegionConfig(EventRegion.SOUTH_OXON, "South Oxfordshire", "southoxon_venue", "southoxon_event"),
]


class Command(BaseCommand):
    help = "Migrate legacy regional event tables into unified events tables. Defaults to dry run."

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Apply changes. Without this flag, the command runs as dry-run and rolls back.",
        )

    def handle(self, *args, **options):
        commit = options["commit"]
        dry_run = not commit

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run mode: no data will be committed."))
        else:
            self.stdout.write(self.style.WARNING("Commit mode: data changes will be written."))

        table_names = set(connection.introspection.table_names())
        existing_user_ids = set(get_user_model().objects.values_list("id", flat=True))

        migrated_venues = 0
        migrated_events = 0
        skipped_events = 0
        skipped_regions = 0

        with transaction.atomic():
            for cfg in LEGACY_REGIONS:
                if cfg.venue_table not in table_names or cfg.event_table not in table_names:
                    skipped_regions += 1
                    self.stdout.write(f"Skipping {cfg.label}: missing legacy table(s).")
                    continue

                self.stdout.write(f"Processing {cfg.label}...")

                legacy_venues = self._fetch_legacy_venues(cfg.venue_table)
                legacy_events = self._fetch_legacy_events(cfg.event_table)

                venue_id_map: dict[int, int] = {}

                for row in legacy_venues:
                    new_venue_id, created = self._upsert_venue(cfg.region, row)
                    venue_id_map[row["id"]] = new_venue_id
                    if created:
                        migrated_venues += 1

                for row in legacy_events:
                    if self._event_exists(cfg.region, row):
                        skipped_events += 1
                        continue

                    venue_id = venue_id_map.get(row["venue_id"])
                    if venue_id is None:
                        skipped_events += 1
                        continue

                    submitted_by_id = row.get("submitted_by_id")
                    reviewed_by_id = row.get("reviewed_by_id")

                    if submitted_by_id and submitted_by_id not in existing_user_ids:
                        submitted_by_id = None
                    if reviewed_by_id and reviewed_by_id not in existing_user_ids:
                        reviewed_by_id = None

                    Event.objects.create(
                        region=cfg.region,
                        title=row.get("title") or "Untitled event",
                        slug=self._unique_event_slug(row.get("slug"), row.get("title"), cfg.region, row["id"]),
                        venue_id=venue_id,
                        category=self._safe_category(row.get("category")),
                        start_at=row.get("start_at") or timezone.now(),
                        end_at=row.get("end_at"),
                        description=row.get("description") or "",
                        status=self._safe_status(row.get("status")),
                        submitted_by_id=submitted_by_id,
                        reviewed_by_id=reviewed_by_id,
                        reviewed_at=row.get("reviewed_at"),
                        review_note=row.get("review_note") or "",
                        is_featured=bool(row.get("is_featured")),
                        is_public=bool(row.get("is_public", True)),
                        is_cancelled=bool(row.get("is_cancelled")),
                        cancelled_at=row.get("cancelled_at"),
                        cancellation_note=row.get("cancellation_note") or "",
                        created_at=row.get("created_at") or timezone.now(),
                        updated_at=row.get("updated_at") or timezone.now(),
                    )
                    migrated_events += 1

            summary = (
                f"Summary: venues created={migrated_venues}, events created={migrated_events}, "
                f"events skipped={skipped_events}, regions skipped={skipped_regions}"
            )
            self.stdout.write(self.style.SUCCESS(summary))

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry run complete. Transaction rolled back."))
            else:
                self.stdout.write(self.style.SUCCESS("Migration complete. Changes committed."))

    def _fetch_legacy_venues(self, table_name: str) -> list[dict[str, Any]]:
        query = f"""
            SELECT
                id, name, slug,
                address_line_1, address_line_2, town, postcode,
                website, contact_email, phone,
                is_active, created_at, updated_at
            FROM {table_name}
        """
        return self._fetch_dict_rows(query)

    def _fetch_legacy_events(self, table_name: str) -> list[dict[str, Any]]:
        query = f"""
            SELECT
                id, title, slug, category,
                start_at, end_at,
                description,
                status,
                submitted_by_id,
                reviewed_by_id,
                reviewed_at,
                review_note,
                is_featured,
                is_public,
                is_cancelled,
                cancelled_at,
                cancellation_note,
                venue_id,
                created_at,
                updated_at
            FROM {table_name}
        """
        return self._fetch_dict_rows(query)

    def _fetch_dict_rows(self, query: str) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def _upsert_venue(self, region: str, row: dict[str, Any]) -> tuple[int, bool]:
        legacy_slug = row.get("slug") or ""

        if legacy_slug:
            existing = Venue.objects.filter(slug=legacy_slug).first()
            if existing:
                return existing.id, False

        base_name = (row.get("name") or "Venue").strip() or "Venue"
        candidate_slug = legacy_slug or slugify(base_name)
        unique_slug = self._unique_venue_slug(candidate_slug, region, row["id"])

        venue = Venue.objects.create(
            name=base_name,
            slug=unique_slug,
            address_line_1=row.get("address_line_1") or "",
            address_line_2=row.get("address_line_2") or "",
            town=row.get("town") or "",
            postcode=row.get("postcode") or "",
            website=row.get("website") or "",
            contact_email=row.get("contact_email") or "",
            phone=row.get("phone") or "",
            is_active=bool(row.get("is_active", True)),
            created_at=row.get("created_at") or timezone.now(),
            updated_at=row.get("updated_at") or timezone.now(),
        )
        return venue.id, True

    def _event_exists(self, region: str, row: dict[str, Any]) -> bool:
        legacy_slug = row.get("slug") or ""
        if legacy_slug and Event.objects.filter(region=region, slug=legacy_slug).exists():
            return True

        return Event.objects.filter(
            region=region,
            title=row.get("title") or "",
            start_at=row.get("start_at"),
        ).exists()

    def _safe_category(self, value: str | None) -> str:
        allowed = {choice[0] for choice in Event._meta.get_field("category").choices}
        return value if value in allowed else Event._meta.get_field("category").default

    def _safe_status(self, value: str | None) -> str:
        allowed = {choice[0] for choice in EventStatus.choices}
        return value if value in allowed else EventStatus.PENDING

    def _unique_venue_slug(self, slug: str | None, region: str, legacy_id: int) -> str:
        base = (slug or "").strip() or f"venue-{region}-{legacy_id}"
        candidate = base
        counter = 2
        while Venue.objects.filter(slug=candidate).exists():
            candidate = f"{base}-{counter}"
            counter += 1
        return candidate

    def _unique_event_slug(self, slug: str | None, title: str | None, region: str, legacy_id: int) -> str:
        base = (slug or "").strip() or slugify(title or "") or f"event-{region}-{legacy_id}"
        candidate = base
        counter = 2
        while Event.objects.filter(slug=candidate).exists():
            candidate = f"{base}-{counter}"
            counter += 1
        return candidate
