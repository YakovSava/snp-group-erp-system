import asyncio

from fastapi import APIRouter, Depends

from ..deps import verify_service_token
from ..publishers.base import SocialPublisher
from ..publishers.registry import ALL_PLATFORMS, build_publishers
from ..schemas import PublishRequest, PublishResponse, PublishResult

router = APIRouter(prefix="/v1/posts", tags=["posts"])


async def _publish_with(publisher: SocialPublisher, request: PublishRequest) -> PublishResult:
    try:
        return await publisher.publish(request)
    except Exception as exc:  # one network's failure must never block the rest
        return PublishResult(platform=publisher.platform, status="error", detail=str(exc))


@router.post("/publish", response_model=PublishResponse)
async def publish_post(request: PublishRequest, _: None = Depends(verify_service_token)) -> PublishResponse:
    requested = ALL_PLATFORMS if "all" in request.platforms else request.platforms

    results: list[PublishResult] = []
    tasks = []
    for publisher in build_publishers():
        if publisher.platform not in requested:
            continue
        if not publisher.is_configured():
            results.append(
                PublishResult(platform=publisher.platform, status="skipped_unconfigured", detail="No credentials configured")
            )
            continue
        tasks.append(_publish_with(publisher, request))

    if tasks:
        results.extend(await asyncio.gather(*tasks))

    return PublishResponse(results=results)
