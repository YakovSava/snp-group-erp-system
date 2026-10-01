from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import FormView, ListView

from .forms import DocumentConversionForm, PhotoConversionForm, VideoConversionForm
from .models import ConversionHistory, ConversionJob
from .tasks import process_conversion_job


class BaseConversionView(LoginRequiredMixin, FormView):
    kind = None
    success_url_name = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["jobs"] = ConversionJob.objects.filter(user=self.request.user, kind=self.kind)[:10]
        return context

    def form_valid(self, form):
        job = ConversionJob.objects.create(
            user=self.request.user,
            kind=self.kind,
            source_file=form.cleaned_data["source_file"],
            target_format=form.cleaned_data["target_format"],
        )
        process_conversion_job.delay(job.pk)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(self.success_url_name)


class PhotoConversionView(BaseConversionView):
    kind = ConversionJob.KIND_IMAGE
    form_class = PhotoConversionForm
    template_name = "utilities/photo.html"
    success_url_name = "utilities:photo"


class VideoConversionView(BaseConversionView):
    kind = ConversionJob.KIND_VIDEO
    form_class = VideoConversionForm
    template_name = "utilities/video.html"
    success_url_name = "utilities:video"


class DocumentConversionView(BaseConversionView):
    kind = ConversionJob.KIND_DOCUMENT
    form_class = DocumentConversionForm
    template_name = "utilities/files.html"
    success_url_name = "utilities:files"


class HistoryListView(LoginRequiredMixin, ListView):
    model = ConversionHistory
    template_name = "utilities/history.html"
    context_object_name = "history_items"
    paginate_by = 50

    def get_queryset(self):
        return ConversionHistory.objects.filter(user=self.request.user)
