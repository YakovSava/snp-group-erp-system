from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.CatalogItemListView.as_view(), name="item_list"),
    path("items/create/", views.CatalogItemCreateView.as_view(), name="item_create"),
    path("items/<int:pk>/", views.CatalogItemDetailView.as_view(), name="item_detail"),
    path("items/<int:pk>/edit/", views.CatalogItemUpdateView.as_view(), name="item_edit"),
    path("items/<int:pk>/delete/", views.CatalogItemDeleteView.as_view(), name="item_delete"),
    path("export/", views.CatalogExportView.as_view(), name="export"),
    path("import/", views.CatalogImportUploadView.as_view(), name="import_upload"),
    path("import/review/", views.CatalogImportReviewView.as_view(), name="import_review"),
    path("import/cancel/", views.CatalogImportCancelView.as_view(), name="import_cancel"),
]
