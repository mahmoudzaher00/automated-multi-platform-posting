from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    bluesky_identifier: str = ""
    bluesky_app_password: SecretStr = SecretStr("")
    mastodon_base_url: str = "https://mastodon.social"
    mastodon_access_token: SecretStr = SecretStr("")
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_channel: str = ""
    dev_api_key: SecretStr = SecretStr("")
    wordpress_site: str = ""
    wordpress_access_token: SecretStr = SecretStr("")
