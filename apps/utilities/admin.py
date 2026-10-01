from django.contrib import admin

from .models import ConversionHistory, ConversionJob


@admin.register(ConversionJob)
class ConversionJobAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "kind", "detected_source_format", "target_format", "status", "created_at", "expires_at")
    list_filter = ("kind", "status")
    readonly_fields = ("created_at",)


@admin.register(ConversionHistory)
class ConversionHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "created_at")
    readonly_fields = ("user", "action", "created_at")
    search_fields = ("action", "user__username")
