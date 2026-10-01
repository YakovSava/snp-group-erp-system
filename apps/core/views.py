from django.http import HttpResponse
from django.views.generic import TemplateView


class LandingView(TemplateView):
    template_name = "core/landing.html"


def robots_txt(request):
    content = "User-agent: *\nDisallow: /\n"
    return HttpResponse(content, content_type="text/plain")


def sitemap_xml(request):
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>\n'
    )
    return HttpResponse(content, content_type="application/xml")
