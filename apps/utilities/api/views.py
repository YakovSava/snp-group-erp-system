from rest_framework import mixins, viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from ..models import ConversionHistory, ConversionJob
from ..tasks import process_conversion_job
from .serializers import ConversionHistorySerializer, ConversionJobSerializer


class ConversionJobViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Powers the site's own upload + status-polling UI (/api/internal/)."""

    serializer_class = ConversionJobSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ConversionJob.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        job = serializer.save(user=self.request.user)
        process_conversion_job.delay(job.pk)


class ConversionHistoryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Read-only integration surface for other ESB components (/api/v1/)."""

    serializer_class = ConversionHistorySerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = ConversionHistory.objects.all()
