from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView, ListView

from .forms import PostForm, SalesPostForm
from .models import Post, PostAttachment, SalesPost, SalesPostAttachment


class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = "posts/post_list.html"
    context_object_name = "posts"
    paginate_by = 20


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


class SalesPostListView(LoginRequiredMixin, ListView):
    model = SalesPost
    template_name = "posts/salespost_list.html"
    context_object_name = "sales_posts"
    paginate_by = 20


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
