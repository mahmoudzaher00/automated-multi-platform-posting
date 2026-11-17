from html import escape
from urllib.parse import quote

import httpx

from app.domain.posting import Message, PublishedPost, PublishingError
from app.platforms.http import bearer, request_json, required_text, timestamp


class WordPressPublisher:
    name = "WordPress.com"

    def __init__(self, client: httpx.AsyncClient, site: str, token: str):
        self._client = client
        self._site = site
        self._token = token

    async def publish(self, message: Message) -> PublishedPost:
        if not self._site or not self._token:
            raise PublishingError("Set WORDPRESS_SITE and WORDPRESS_ACCESS_TOKEN.")

        site_url = f"https://public-api.wordpress.com/rest/v1.1/sites/{quote(self._site, safe='')}"
        headers = bearer(self._token)
        site = await request_json(self._client, "GET", site_url, headers=headers)
        link = escape(message.link)
        before_link = escape(message.text[:message.link_start])
        after_link = escape(message.text[message.link_end:])
        content = f'<p>{before_link}<a href="{link}">{link}</a>{after_link}</p>'
        data = await request_json(
            self._client,
            "POST",
            f"{site_url}/posts/new",
            headers=headers,
            data={"title": "Update", "content": content, "status": "publish"},
        )
        if data.get("status") not in ("publish", "private"):
            raise PublishingError("WordPress did not confirm publication.")
        public = (
            data["status"] == "publish"
            and site.get("is_private") is False
            and not site.get("is_coming_soon")
            and not data.get("has_password")
        )
        return PublishedPost(required_text(data, "URL"), public, timestamp(data, "date"))
