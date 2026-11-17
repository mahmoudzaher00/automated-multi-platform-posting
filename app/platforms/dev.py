import httpx

from app.domain.posting import Message, PublishedPost, PublishingError
from app.platforms.http import request_json, required_text, timestamp


class DevPublisher:
    name = "DEV Community"

    def __init__(self, client: httpx.AsyncClient, api_key: str):
        self._client = client
        self._api_key = api_key

    async def publish(self, message: Message) -> PublishedPost:
        if not self._api_key:
            raise PublishingError("Set DEV_API_KEY.")

        body = f"{message.text[:message.link_start]}<{message.link}>{message.text[message.link_end:]}"
        data = await request_json(
            self._client,
            "POST",
            "https://dev.to/api/articles",
            headers={
                "Accept": "application/vnd.forem.api-v1+json",
                "api-key": self._api_key,
            },
            json={"article": {"title": "Update", "body_markdown": body, "published": True}},
        )
        if not data.get("published_at"):
            raise PublishingError("DEV did not confirm publication.")
        return PublishedPost(required_text(data, "url"), True, timestamp(data, "published_at"))
