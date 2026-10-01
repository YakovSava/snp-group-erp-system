from django.urls import path

from . import views

app_name = "agent"

urlpatterns = [
    path("", views.chat_page, name="chat"),
    path("send/", views.send_message, name="send_message"),
    path("new/", views.new_conversation, name="new_conversation"),
]
