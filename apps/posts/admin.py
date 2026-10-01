from django.contrib import admin

from .models import Post, PostAttachment, SalesPost, SalesPostAttachment


class PostAttachmentInline(admin.TabularInline):
    model = PostAttachment
    extra = 0


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "short_text", "send_to_marketplace", "created_by", "created_at")
    list_filter = ("send_to_marketplace",)
    inlines = [PostAttachmentInline]
    fields = (
        "text",
        "instagram_text",
        "telegram_text",
        "facebook_text",
        "common_social_text",
        "internal_comment",
        "send_to_marketplace",
        "created_by",
    )

    @admin.display(description="Текст")
    def short_text(self, obj):
        return obj.text[:60]


class SalesPostAttachmentInline(admin.TabularInline):
    model = SalesPostAttachment
    extra = 0


@admin.register(SalesPost)
class SalesPostAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "price_amd", "is_auto_generated", "created_by", "created_at")
    list_filter = ("is_auto_generated",)
    inlines = [SalesPostAttachmentInline]
