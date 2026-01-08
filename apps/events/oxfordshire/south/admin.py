from django.contrib import admin

from .models import Event, Venue


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "town", "postcode", "website", "is_active")
    list_filter = ("is_active", "town")
    search_fields = ("name", "town", "postcode")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "venue", "start_at", "status", "is_public", "is_featured")
    list_filter = ("status", "is_public", "is_featured", "category", "venue")
    search_fields = ("title", "venue__name", "description")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "start_at"
    autocomplete_fields = ("venue",)
