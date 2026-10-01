from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from ..models import Post, SalesPost
from .serializers import PostSerializer, SalesPostSerializer


class PostViewSet(viewsets.ModelViewSet):
    """Token-authenticated integration surface for other ESB components."""

    queryset = Post.objects.prefetch_related("attachments").all()
    serializer_class = PostSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SalesPostViewSet(viewsets.ModelViewSet):
    queryset = SalesPost.objects.prefetch_related("attachments").all()
    serializer_class = SalesPostSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
