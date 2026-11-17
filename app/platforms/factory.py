import httpx

from app.config import Settings
from app.domain.posting import Publisher
from app.platforms.bluesky import BlueskyPublisher
from app.platforms.dev import DevPublisher
from app.platforms.mastodon import MastodonPublisher
from app.platforms.telegram import TelegramPublisher
from app.platforms.wordpress import WordPressPublisher


def build_publishers(client: httpx.AsyncClient, settings: Settings) -> tuple[Publisher, ...]:
    return (
        BlueskyPublisher(client, settings.bluesky_identifier, settings.bluesky_app_password.get_secret_value()),
        MastodonPublisher(client, settings.mastodon_base_url, settings.mastodon_access_token.get_secret_value()),
        TelegramPublisher(client, settings.telegram_bot_token.get_secret_value(), settings.telegram_channel),
        DevPublisher(client, settings.dev_api_key.get_secret_value()),
        WordPressPublisher(client, settings.wordpress_site, settings.wordpress_access_token.get_secret_value()),
    )
