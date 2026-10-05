import httpx

from .config import Settings


def new_async_client(settings: Settings, **kwargs) -> httpx.AsyncClient:
    """httpx.AsyncClient routed through OUTBOUND_PROXY_URL, when set.

    All publishers go through this instead of calling httpx.AsyncClient(...)
    directly, so one setting controls how every network's traffic reaches
    the outside world.
    """
    return httpx.AsyncClient(proxy=settings.outbound_proxy_url or None, **kwargs)
