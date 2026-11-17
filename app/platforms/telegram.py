import re
from datetime import UTC, datetime

import httpx

from app.domain.posting import Message, PublishedPost, PublishingError
from app.platforms.http import request_json


class TelegramPublisher:
    name = "Telegram"

    def __init__(self, client: httpx.AsyncClient, token: str, channel: str):
        self._client = client
        self._token = token
        self._channel = channel.removeprefix("@")

    async def publish(self, message: Message) -> PublishedPost:
        if not self._token or not self._channel:
            raise PublishingError("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL.")
        if not re.fullmatch(r"[a-zA-Z0-9_]+", self._channel):
            raise PublishingError("TELEGRAM_CHANNEL must be a public channel username.")

        data = await request_json(
            self._client,
            "POST",
            f"https://api.telegram.org/bot{self._token}/sendMessage",
            json={"chat_id": f"@{self._channel}", "text": message.text},
        )
        post = data.get("result")
        if data.get("ok") is not True or not isinstance(post, dict):
            raise PublishingError("Telegram did not confirm publication.")

        post_id = post.get("message_id")
        epoch = post.get("date")
        if type(post_id) is not int or type(epoch) is not int or post_id <= 0:
            raise PublishingError("Telegram returned incomplete publication details.")

        try:
            posted_at = datetime.fromtimestamp(epoch, UTC)
        except (OverflowError, OSError, ValueError):
            raise PublishingError("Telegram returned an invalid publication date.") from None
        chat = post.get("chat")
        public = isinstance(chat, dict) and chat.get("type") == "channel" and bool(chat.get("username"))
        url = f"https://t.me/{self._channel}/{post_id}" if public else None
        return PublishedPost(url, public, posted_at)
