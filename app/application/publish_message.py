import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.posting import Message, PublishedPost, Publisher, PublishingError


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PostingResult:
    platform: str
    post: PublishedPost | None = None
    error: str | None = None


class PublishMessage:
    def __init__(self, publishers: Sequence[Publisher]):
        self._publishers = tuple(publishers)

    async def execute(self, message: Message) -> list[PostingResult]:
        return await asyncio.gather(
            *(self._publish_one(publisher, message) for publisher in self._publishers)
        )

    async def _publish_one(self, publisher: Publisher, message: Message) -> PostingResult:
        try:
            return PostingResult(publisher.name, post=await publisher.publish(message))
        except PublishingError as error:
            return PostingResult(publisher.name, error=str(error))
        except Exception as error:
            logger.error("%s publisher raised %s", publisher.name, type(error).__name__)
            return PostingResult(publisher.name, error="Unexpected publishing error.")
