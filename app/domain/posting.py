from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class Message:
    text: str
    link: str
    link_start: int

    @property
    def link_end(self) -> int:
        return self.link_start + len(self.link)


@dataclass(frozen=True)
class PublishedPost:
    url: str | None
    public: bool
    published_at: datetime


class PublishingError(Exception):
    pass


class Publisher(Protocol):
    @property
    def name(self) -> str: ...

    async def publish(self, message: Message) -> PublishedPost: ...
