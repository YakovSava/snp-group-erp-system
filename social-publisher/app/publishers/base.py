from abc import ABC, abstractmethod
from typing import ClassVar

from ..schemas import PublishRequest, PublishResult


class SocialPublisher(ABC):
    """Common interface every network adapter implements.

    The orchestrator in routers/publish.py only ever talks to instances
    through this interface — it never knows or cares which network it's
    driving. Adding an 8th network is just a new subclass + one line in
    registry.py.
    """

    platform: ClassVar[str]

    @abstractmethod
    def is_configured(self) -> bool:
        """Whether this adapter has the credentials it needs to run.

        Lets the orchestrator skip a network with an empty/missing token
        without treating that as an error.
        """

    @abstractmethod
    async def publish(self, request: PublishRequest) -> PublishResult:
        ...
