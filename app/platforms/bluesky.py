from datetime import UTC, datetime

import httpx

from app.domain.posting import Message, PublishedPost, PublishingError
from app.platforms.http import bearer, request_json, required_text

XRPC = "https://bsky.social/xrpc"
POST_COLLECTION = "app.bsky.feed.post"


class BlueskyPublisher:
    name = "Bluesky"

    def __init__(self, client: httpx.AsyncClient, identifier: str, password: str):
        self._client = client
        self._identifier = identifier
        self._password = password

    async def publish(self, message: Message) -> PublishedPost:
        if not self._identifier or not self._password:
            raise PublishingError("Set BLUESKY_IDENTIFIER and BLUESKY_APP_PASSWORD.")

        session = await request_json(
            self._client,
            "POST",
            f"{XRPC}/com.atproto.server.createSession",
            json={"identifier": self._identifier, "password": self._password},
        )
        did = required_text(session, "did")
        token = required_text(session, "accessJwt")
        posted_at = datetime.now(UTC)
        start = len(message.text[:message.link_start].encode("utf-8"))
        end = start + len(message.link.encode("utf-8"))
        record = {
            "$type": POST_COLLECTION,
            "text": message.text,
            "createdAt": posted_at.isoformat(),
            "facets": [
                {
                    "index": {"byteStart": start, "byteEnd": end},
                    "features": [{"$type": "app.bsky.richtext.facet#link", "uri": message.link}],
                }
            ],
        }
        data = await request_json(
            self._client,
            "POST",
            f"{XRPC}/com.atproto.repo.createRecord",
            headers=bearer(token),
            json={"repo": did, "collection": POST_COLLECTION, "record": record},
        )
        uri = required_text(data, "uri")
        prefix = f"at://{did}/{POST_COLLECTION}/"
        if not uri.startswith(prefix) or not uri.removeprefix(prefix):
            raise PublishingError("Bluesky returned an invalid post URI.")
        record_key = uri.removeprefix(prefix)
        return PublishedPost(f"https://bsky.app/profile/{did}/post/{record_key}", True, posted_at)
