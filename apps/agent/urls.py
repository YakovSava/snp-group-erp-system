from django.urls import path

from . import smm, views

app_name = "agent"

urlpatterns = [
    path("", views.chat_page, name="chat"),
    path("send/", views.send_message, name="send_message"),
    path("new/", views.new_conversation, name="new_conversation"),
    path("smm/", smm.smm_tool_page, name="smm_tool"),
    path("smm/generate/", smm.smm_generate, name="smm_generate"),
    path("smm/refine/", smm.smm_refine, name="smm_refine"),
    path("smm/discard/", smm.smm_discard, name="smm_discard"),
    path("smm/accept/", smm.smm_accept, name="smm_accept"),
]
