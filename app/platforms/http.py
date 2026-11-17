from datetime import datetime
from typing import Any

import httpx

from app.domain.posting import PublishingError


async def request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **options: Any,
) -> dict[str, Any]:
    try:
        response = await client.request(method, url, **options)
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        status = error.response.status_code
        raise PublishingError(f"Platform returned HTTP {status}.") from None
    except httpx.TimeoutException:
        raise PublishingError("Platform request timed out. Check the platform before retrying.") from None
    except httpx.RequestError:
        raise PublishingError("Could not reach the platform.") from None
    except httpx.InvalidURL:
        raise PublishingError("Platform URL is invalid.") from None

    try:
        data = response.json()
    except ValueError:
        raise PublishingError("Platform returned invalid JSON.") from None

    if not isinstance(data, dict):
        raise PublishingError("Platform returned an unexpected response.")
    return data


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def required_text(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value:
        raise PublishingError(f"Platform response is missing {field}.")
    return value


def timestamp(data: dict[str, Any], field: str) -> datetime:
    try:
        value = datetime.fromisoformat(required_text(data, field).replace("Z", "+00:00"))
    except ValueError:
        raise PublishingError("Platform returned an invalid publication date.") from None
    if value.tzinfo is None:
        raise PublishingError("Platform returned a publication date without a time zone.")
    return value
