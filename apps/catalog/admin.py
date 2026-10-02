from django.contrib import admin

from .models import CatalogItem


@admin.register(CatalogItem)
class CatalogItemAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "article", "amount_amd", "amount_rub", "amount_usd", "supplier", "updated_at")
    search_fields = ("title", "article", "comment", "description", "supplier")
    list_filter = ("supplier",)
