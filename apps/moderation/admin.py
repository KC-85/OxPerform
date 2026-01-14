from django.contrib import admin
from .models import EventModerationLog


@admin.register(EventModerationLog)
class EventModerationLogAdmin(admin.ModelAdmin):
    list_display = ("acted_at", "region", "event_id", "action", "actor", "note_short")
    list_filter = ("region", "action", "acted_at")
    search_fields = ("event_id", "note", "actor__username", "actor__email")
    ordering = ("-acted_at",)

    def note_short(self, obj):
        return (obj.note[:40] + "…") if obj.note and len(obj.note) > 40 else obj.note

    note_short.short_description = "Note"
