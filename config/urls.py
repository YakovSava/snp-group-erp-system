from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as serve_static

from apps.core.views import robots_txt, sitemap_xml

admin.site.site_header = "SNP ESB"
admin.site.site_title = "SNP ESB"
admin.site.index_title = "Администрирование"

urlpatterns = [
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap_xml"),
    path("admin/", admin.site.urls),
    path("api/internal/", include("apps.utilities.api.internal_urls")),
    path("api/v1/", include("apps.posts.api.v1_urls")),
    path("api/v1/", include("apps.utilities.api.v1_urls")),
    path("i18n/", include("django.conf.urls.i18n")),
]

urlpatterns += i18n_patterns(
    path("accounts/", include("apps.accounts.urls")),
    path("utilities/", include("apps.utilities.urls")),
    path("agent/", include("apps.agent.urls")),
    path("catalog/", include("apps.catalog.urls")),
    path("", include("apps.posts.urls")),
    path("", include("apps.core.urls")),
    prefix_default_language=True,
)

# django.conf.urls.static.static() no-ops when DEBUG=False, which doesn't
# suit us: this is a small internal tool with no nginx/object-storage layer
# in front of it, so media is always served directly by Django.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve_static, {"document_root": settings.MEDIA_ROOT}),
]
