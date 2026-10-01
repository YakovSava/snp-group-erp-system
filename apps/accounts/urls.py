from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.SnpLoginView.as_view(), name="login"),
    path("logout/", views.SnpLogoutView.as_view(), name="logout"),
    path("security/", views.security, name="security"),
    path("security/credentials/<int:pk>/delete/", views.credential_delete, name="credential_delete"),
    path("webauthn/register/begin/", views.webauthn_register_begin, name="webauthn_register_begin"),
    path("webauthn/register/complete/", views.webauthn_register_complete, name="webauthn_register_complete"),
    path("webauthn/login/begin/", views.webauthn_login_begin, name="webauthn_login_begin"),
    path("webauthn/login/complete/", views.webauthn_login_complete, name="webauthn_login_complete"),
]
