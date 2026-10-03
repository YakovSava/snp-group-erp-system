import httpx
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.core import social_client

from .forms import PostForm, SalesPostForm
from .models import Post, PostAttachment, PostPublication, SalesPost, SalesPostAttachment

PLATFORM_LABELS = {
    "facebook": "Facebook",
    "instagram": "Instagram",
    "telegram": "Telegram",
    "threads": "Threads",
    "x": "X",
    "vk": "VK",
    "max": "MAX",
}


class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = "posts/post_list.html"
    context_object_name = "posts"
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().prefetch_related("attachments")


class PostDetailView(LoginRequiredMixin, DetailView):
    model = Post
    template_name = "posts/post_detail.html"
    context_object_name = "post"


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = "posts/post_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        with transaction.atomic():
            response = super().form_valid(form)
            for uploaded_file in form.cleaned_data.get("attachments") or []:
                PostAttachment.objects.create(post=self.object, file=uploaded_file)
        messages.success(self.request, _("Пост создан."))
        return response

    def get_success_url(self):
        return reverse("posts:post_detail", args=[self.object.pk])


class PostPublishView(LoginRequiredMixin, View):
    """The "Отправить во все соцсети" button on the post detail page — fans
    the post out via social_client.publish_to_all and records one
    PostPublication per platform the service reported on (including
    networks it skipped for lack of credentials)."""

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)

        try:
            results = social_client.publish_to_all(post)
        except httpx.HTTPError:
            messages.error(request, _("Сервис публикации временно недоступен. Попробуйте позже."))
            return redirect("posts:post_detail", pk=post.pk)

        PostPublication.objects.bulk_create(
            PostPublication(
                post=post,
                platform=result["platform"],
                status=result["status"],
                detail=result.get("detail", ""),
                external_url=result.get("external_url") or "",
            )
            for result in results
        )

        for result in results:
            label = PLATFORM_LABELS.get(result["platform"], result["platform"])
            if result["status"] == PostPublication.STATUS_SUCCESS:
                messages.success(request, f"{label}: {_('опубликовано')}")
            elif result["status"] == PostPublication.STATUS_SKIPPED:
                messages.info(request, f"{label}: {_('пропущено (нет токена)')}")
            else:
                messages.error(request, f"{label}: {result.get('detail') or _('ошибка')}")

        return redirect("posts:post_detail", pk=post.pk)


class SalesPostListView(LoginRequiredMixin, ListView):
    model = SalesPost
    template_name = "posts/salespost_list.html"
    context_object_name = "sales_posts"
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().prefetch_related("attachments")


class SalesPostDetailView(LoginRequiredMixin, DetailView):
    model = SalesPost
    template_name = "posts/salespost_detail.html"
    context_object_name = "sales_post"


class SalesPostCreateView(LoginRequiredMixin, CreateView):
    model = SalesPost
    form_class = SalesPostForm
    template_name = "posts/salespost_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        for uploaded_file in form.cleaned_data.get("attachments") or []:
            SalesPostAttachment.objects.create(sales_post=self.object, file=uploaded_file)
        messages.success(self.request, _("Пост в сетях продажи создан."))
        return response

    def get_success_url(self):
        return reverse("posts:salespost_detail", args=[self.object.pk])
