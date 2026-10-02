from rest_framework import serializers

from ..models import Post, PostAttachment, PostTranslation, SalesPost, SalesPostAttachment


class PostAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostAttachment
        fields = ["id", "file", "uploaded_at"]
        read_only_fields = fields


class PostTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostTranslation
        fields = ["language", "text", "created_at"]
        read_only_fields = fields


class PostSerializer(serializers.ModelSerializer):
    """Full surface, including the per-platform texts that are hidden from
    the public web form — other ESB components (publishing bots) are the
    intended consumers of those fields here.
    """

    attachments = PostAttachmentSerializer(many=True, read_only=True)
    translations = PostTranslationSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "text",
            "meta_text",
            "telegram_text",
            "common_social_text",
            "price_amount",
            "price_currency",
            "internal_comment",
            "send_to_marketplace",
            "attachments",
            "translations",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "attachments", "translations", "created_by", "created_at", "updated_at"]


class SalesPostAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesPostAttachment
        fields = ["id", "file", "uploaded_at"]
        read_only_fields = fields


class SalesPostSerializer(serializers.ModelSerializer):
    attachments = SalesPostAttachmentSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = SalesPost
        fields = [
            "id",
            "title",
            "text",
            "price_amd",
            "source_post",
            "is_auto_generated",
            "attachments",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_auto_generated", "attachments", "created_by", "created_at", "updated_at"]
