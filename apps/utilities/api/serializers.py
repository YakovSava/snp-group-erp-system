from rest_framework import serializers

from ..models import ConversionHistory, ConversionJob


class ConversionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversionJob
        fields = [
            "id",
            "kind",
            "source_file",
            "target_format",
            "detected_source_format",
            "status",
            "error_message",
            "result_file",
            "created_at",
            "expires_at",
        ]
        read_only_fields = [
            "id",
            "detected_source_format",
            "status",
            "error_message",
            "result_file",
            "created_at",
            "expires_at",
        ]


class ConversionHistorySerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = ConversionHistory
        fields = ["id", "user", "action", "created_at"]
        read_only_fields = fields
