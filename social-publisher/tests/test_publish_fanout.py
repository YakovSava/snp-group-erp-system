from fastapi.testclient import TestClient

from app.deps import verify_service_token
from app.main import app
from app.publishers.base import SocialPublisher
from app.schemas import PublishRequest, PublishResult


class ConfiguredPublisher(SocialPublisher):
    platform = "configured"

    def is_configured(self) -> bool:
        return True

    async def publish(self, request: PublishRequest) -> PublishResult:
        return PublishResult(platform=self.platform, status="success", detail="ok")


class UnconfiguredPublisher(SocialPublisher):
    platform = "unconfigured"

    def is_configured(self) -> bool:
        return False

    async def publish(self, request: PublishRequest) -> PublishResult:
        raise AssertionError("must not be called when unconfigured")


class BrokenPublisher(SocialPublisher):
    platform = "broken"

    def is_configured(self) -> bool:
        return True

    async def publish(self, request: PublishRequest) -> PublishResult:
        raise RuntimeError("platform is down")


def fake_publishers(settings=None):
    return [ConfiguredPublisher(), UnconfiguredPublisher(), BrokenPublisher()]


def test_send_for_all_isolates_unconfigured_and_broken_platforms(monkeypatch):
    import app.routers.publish as publish_module

    monkeypatch.setattr(publish_module, "build_publishers", fake_publishers)
    monkeypatch.setattr(publish_module, "ALL_PLATFORMS", ["configured", "unconfigured", "broken"])
    app.dependency_overrides[verify_service_token] = lambda: None

    client = TestClient(app)
    response = client.post("/v1/posts/publish", json={"text": "hello", "platforms": ["all"]})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    results = {result["platform"]: result for result in response.json()["results"]}

    assert results["configured"]["status"] == "success"
    assert results["unconfigured"]["status"] == "skipped_unconfigured"
    assert results["broken"]["status"] == "error"
    assert "platform is down" in results["broken"]["detail"]
