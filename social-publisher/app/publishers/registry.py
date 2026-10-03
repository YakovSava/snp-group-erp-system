from ..config import Settings, get_settings
from .base import SocialPublisher
from .facebook import FacebookPublisher
from .instagram import InstagramPublisher
from .max_messenger import MaxPublisher
from .telegram import TelegramPublisher
from .threads import ThreadsPublisher
from .vk import VkPublisher
from .x_twitter import XPublisher

PUBLISHER_CLASSES = [
    FacebookPublisher,
    InstagramPublisher,
    ThreadsPublisher,
    TelegramPublisher,
    MaxPublisher,
    XPublisher,
    VkPublisher,
]


def build_publishers(settings: Settings | None = None) -> list[SocialPublisher]:
    settings = settings or get_settings()
    return [cls(settings) for cls in PUBLISHER_CLASSES]


ALL_PLATFORMS = [cls.platform for cls in PUBLISHER_CLASSES]
