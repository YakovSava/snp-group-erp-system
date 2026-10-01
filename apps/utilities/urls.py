from django.urls import path

from . import views

app_name = "utilities"

urlpatterns = [
    path("photo/", views.PhotoConversionView.as_view(), name="photo"),
    path("video/", views.VideoConversionView.as_view(), name="video"),
    path("files/", views.DocumentConversionView.as_view(), name="files"),
    path("history/", views.HistoryListView.as_view(), name="history"),
]
