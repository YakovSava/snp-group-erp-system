import os
import uuid

import httpx
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from apps.core import ai_client

from .forms import CatalogImportUploadForm, CatalogItemForm, CatalogMappingForm, CatalogSearchForm
from .models import CatalogItem
from .services import excel

SESSION_IMPORT_KEY = "catalog_import"
IMPORT_SUBDIR = "catalog_imports"


def _import_abspath(relative_path):
    return os.path.join(settings.MEDIA_ROOT, relative_path)


def _save_import_file(uploaded_file) -> str:
    import_dir = os.path.join(settings.MEDIA_ROOT, IMPORT_SUBDIR)
    os.makedirs(import_dir, exist_ok=True)
    relative_path = f"{IMPORT_SUBDIR}/{uuid.uuid4().hex}.xlsx"
    with open(_import_abspath(relative_path), "wb") as fh:
        for chunk in uploaded_file.chunks():
            fh.write(chunk)
    return relative_path


def _discard_import(request):
    state = request.session.get(SESSION_IMPORT_KEY)
    if state and state.get("file_path"):
        try:
            os.remove(_import_abspath(state["file_path"]))
        except OSError:
            pass
    request.session.pop(SESSION_IMPORT_KEY, None)


class CatalogItemListView(LoginRequiredMixin, ListView):
    model = CatalogItem
    template_name = "catalog/item_list.html"
    context_object_name = "items"
    paginate_by = 50

    def get_queryset(self):
        self.form = CatalogSearchForm(self.request.GET or None)
        qs = CatalogItem.objects.all()
        if not self.form.is_valid():
            return qs

        q = self.form.cleaned_data.get("q", "").strip()
        field = self.form.cleaned_data.get("field") or "all"
        if not q:
            return qs

        if field == "title":
            return qs.filter(title__icontains=q)
        if field == "comment":
            return qs.filter(comment__icontains=q)
        if field == "price":
            return qs.filter(
                Q(amount_amd__icontains=q) | Q(amount_rub__icontains=q) | Q(amount_usd__icontains=q)
            )
        return qs.filter(
            Q(title__icontains=q)
            | Q(article__icontains=q)
            | Q(description__icontains=q)
            | Q(supplier__icontains=q)
            | Q(comment__icontains=q)
            | Q(amount_amd__icontains=q)
            | Q(amount_rub__icontains=q)
            | Q(amount_usd__icontains=q)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = self.form
        return context


class CatalogItemDetailView(LoginRequiredMixin, DetailView):
    model = CatalogItem
    template_name = "catalog/item_detail.html"
    context_object_name = "item"


class CatalogItemCreateView(LoginRequiredMixin, CreateView):
    model = CatalogItem
    form_class = CatalogItemForm
    template_name = "catalog/item_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, _("Позиция каталога создана."))
        return response

    def get_success_url(self):
        return reverse("catalog:item_detail", args=[self.object.pk])


class CatalogItemUpdateView(LoginRequiredMixin, UpdateView):
    model = CatalogItem
    form_class = CatalogItemForm
    template_name = "catalog/item_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Позиция каталога обновлена."))
        return response

    def get_success_url(self):
        return reverse("catalog:item_detail", args=[self.object.pk])


class CatalogItemDeleteView(LoginRequiredMixin, DeleteView):
    model = CatalogItem
    template_name = "catalog/item_confirm_delete.html"
    context_object_name = "item"

    def get_success_url(self):
        messages.success(self.request, _("Позиция каталога удалена."))
        return reverse("catalog:item_list")


class CatalogExportView(LoginRequiredMixin, View):
    def get(self, request):
        workbook_bytes = excel.build_export_workbook(CatalogItem.objects.order_by("title"))
        response = HttpResponse(
            workbook_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="catalog.xlsx"'
        return response


class CatalogImportUploadView(LoginRequiredMixin, FormView):
    form_class = CatalogImportUploadForm
    template_name = "catalog/import_upload.html"

    def form_valid(self, form):
        uploaded = form.cleaned_data["source_file"]
        headers, sample_rows = excel.read_preview(uploaded)
        if not headers:
            messages.error(self.request, _("Не удалось прочитать файл — он пустой или повреждён."))
            return redirect("catalog:import_upload")

        uploaded.seek(0)
        relative_path = _save_import_file(uploaded)

        try:
            suggestion = ai_client.suggest_catalog_mapping(headers, sample_rows)
        except httpx.HTTPError:
            try:
                os.remove(_import_abspath(relative_path))
            except OSError:
                pass
            messages.error(self.request, _("AI-ассистент временно недоступен. Попробуйте позже."))
            return redirect("catalog:import_upload")

        _discard_import(self.request)
        self.request.session[SESSION_IMPORT_KEY] = {
            "file_path": relative_path,
            "headers": headers,
            "column_fields": suggestion["column_fields"],
            "amount_rub_markup_percent": suggestion.get("amount_rub_markup_percent"),
            "amount_usd_markup_percent": suggestion.get("amount_usd_markup_percent"),
            "notes": suggestion.get("notes", ""),
        }
        return redirect("catalog:import_review")


class CatalogImportReviewView(LoginRequiredMixin, View):
    template_name = "catalog/import_review.html"

    def _build_form(self, state, data=None):
        return CatalogMappingForm(
            data,
            headers=state["headers"],
            initial_column_fields=state["column_fields"],
            initial={
                "amount_rub_markup_percent": state.get("amount_rub_markup_percent"),
                "amount_usd_markup_percent": state.get("amount_usd_markup_percent"),
            },
        )

    def _render(self, request, state, form, column_fields, markup_rub, markup_usd):
        data_rows = excel.read_data_rows(_import_abspath(state["file_path"]))
        preview_items = excel.parse_rows(
            data_rows[:10], state["headers"], column_fields, markup_rub, markup_usd
        )
        return render(request, self.template_name, {
            "form": form,
            "notes": state.get("notes", ""),
            "preview_items": preview_items,
            "total_rows": len(data_rows),
        })

    def get(self, request):
        state = request.session.get(SESSION_IMPORT_KEY)
        if not state:
            return redirect("catalog:import_upload")
        form = self._build_form(state)
        return self._render(
            request, state, form, state["column_fields"],
            state.get("amount_rub_markup_percent"), state.get("amount_usd_markup_percent"),
        )

    def post(self, request):
        state = request.session.get(SESSION_IMPORT_KEY)
        if not state:
            return redirect("catalog:import_upload")

        form = self._build_form(state, data=request.POST)
        if not form.is_valid():
            column_fields = [
                request.POST.get(f"column_{i}", "comment") for i in range(len(state["headers"]))
            ]
            return self._render(
                request, state, form, column_fields,
                request.POST.get("amount_rub_markup_percent"),
                request.POST.get("amount_usd_markup_percent"),
            )

        markup_rub = form.cleaned_data.get("amount_rub_markup_percent")
        markup_usd = form.cleaned_data.get("amount_usd_markup_percent")

        # Two submit buttons share this view: "preview" just re-renders with
        # the edited mapping (same duplicate-field validation, no DB writes)
        # so the employee can check the effect before committing anything.
        if request.POST.get("action") != "commit":
            return self._render(request, state, form, form.column_fields(), markup_rub, markup_usd)

        data_rows = excel.read_data_rows(_import_abspath(state["file_path"]))
        parsed_items = excel.parse_rows(data_rows, state["headers"], form.column_fields(), markup_rub, markup_usd)
        parsed_items, duplicates_in_file = excel.deduplicate_items(parsed_items)

        created, updated = _commit_items(parsed_items, request.user)
        _discard_import(request)

        summary = _("Импорт завершён: добавлено %(created)s, обновлено %(updated)s.") % {
            "created": created, "updated": updated,
        }
        if duplicates_in_file:
            summary += " " + _(
                "Найдено повторов артикула внутри файла: %(count)s (объединены в одну позицию)."
            ) % {"count": duplicates_in_file}
        messages.success(request, summary)
        return redirect("catalog:item_list")


def _commit_items(parsed_items, user):
    created = updated = 0
    for data in parsed_items:
        article = data.get("article") or ""
        # iexact, not exact: articles aren't normalized, so a case-only
        # difference from a previous import shouldn't create a duplicate row.
        existing = CatalogItem.objects.filter(article__iexact=article).first() if article else None
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            existing.created_by = existing.created_by or user
            existing.save()
            updated += 1
        else:
            CatalogItem.objects.create(created_by=user, **data)
            created += 1
    return created, updated


class CatalogImportCancelView(LoginRequiredMixin, View):
    def post(self, request):
        _discard_import(request)
        return redirect("catalog:import_upload")
