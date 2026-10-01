from django.conf import settings


def branding(request):
    return {
        "COMPANY_NAME": "SNP",
        "COMPANY_TAGLINE": "Всё для спецтехники",
        "AVAILABLE_LANGUAGES": settings.LANGUAGES,
    }
