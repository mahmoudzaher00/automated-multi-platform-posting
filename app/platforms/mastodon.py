import httpx

from app.domain.posting import Message, PublishedPost, PublishingError
from app.platforms.http import bearer, request_json, required_text, timestamp


class MastodonPublisher:
    name = "Mastodon"

    def __init__(self, client: httpx.AsyncClient, base_url: str, token: str):
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._token = token

    async def publish(self, message: Message) -> PublishedPost:
        if not self._token:
            raise PublishingError("Set MASTODON_ACCESS_TOKEN.")
        if not self._base_url.startswith("https://"):
            raise PublishingError("MASTODON_BASE_URL must use HTTPS.")

        data = await request_json(
            self._client,
            "POST",
            f"{self._base_url}/api/v1/statuses",
            headers=bearer(self._token),
            data={"status": message.text, "visibility": "public"},
        )
        return PublishedPost(
            url=required_text(data, "url"),
            public=data.get("visibility") in ("public", "unlisted"),
            published_at=timestamp(data, "created_at"),
        )
