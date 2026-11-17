import re
from datetime import UTC, date as CalendarDate, time as ClockTime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, PrivateAttr, ValidationError, model_validator

from app.application.publish_message import PostingResult
from app.domain.posting import Message

LINK_PATTERN = re.compile(r"""(?<![\w@])(?:[a-z][a-z0-9+.-]*://|www\.)[^\s<>"'“”‘’]*""", re.IGNORECASE)


def trim_link_punctuation(link: str) -> str:
    cleaned = link.rstrip(".,!?;:…")
    for opening, closing in (("(", ")"), ("[", "]"), ("{", "}")):
        while cleaned.endswith(closing) and cleaned.count(closing) > cleaned.count(opening):
            cleaned = cleaned[:-1]
    return cleaned


class PostingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Annotated[str, Field(strict=True, min_length=1, max_length=200)]
    _message: Message = PrivateAttr()

    @model_validator(mode="after")
    def validate_link(self) -> "PostingRequest":
        matches = list(LINK_PATTERN.finditer(self.message))
        if len(matches) != 1:
            raise ValueError("Message must contain exactly one HTTP or HTTPS link.")

        match = matches[0]
        raw_link = trim_link_punctuation(match.group())
        try:
            if "\\" in raw_link or not urlsplit(raw_link).netloc:
                raise ValueError
            url = HttpUrl(raw_link)
        except (ValidationError, ValueError) as error:
            raise ValueError("Message must contain a valid HTTP or HTTPS link.") from error

        host = url.host or ""
        if url.username or url.password or ("." not in host and not host.startswith("[")):
            raise ValueError("Message must contain a valid HTTP or HTTPS link.")

        self._message = Message(self.message, raw_link, match.start())
        return self

    def to_message(self) -> Message:
        return self._message


class PlatformResponse(BaseModel):
    platform: str
    status: Literal["success", "failed"]
    posted_url: str | None = None
    public_access: bool = False
    date: CalendarDate | None = None
    time: ClockTime | None = None
    error: str | None = None

    @classmethod
    def from_result(cls, result: PostingResult) -> "PlatformResponse":
        if result.post is None:
            return cls(platform=result.platform, status="failed", error=result.error)

        posted_at = result.post.published_at.astimezone(UTC)
        return cls(
            platform=result.platform,
            status="success",
            posted_url=result.post.url,
            public_access=result.post.public,
            date=posted_at.date(),
            time=posted_at.time().replace(microsecond=0),
        )


class PostingResponse(BaseModel):
    success: bool
    results: list[PlatformResponse]
