# Automated Multi-Platform Posting

A FastAPI service that publishes one short message to Bluesky, Mastodon, Telegram, DEV Community, and WordPress.com through their official APIs.

## Run locally

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

On Windows, activate the environment with `.venv\Scripts\activate` and copy the file with `Copy-Item .env.example .env`. Open [Swagger UI](http://localhost:4000/docs) to try the API.

## Configure publishers

Set credentials for accounts and channels you control in the local `.env` file. Each platform with missing credentials returns a failure while configured platforms continue.

| Platform | Variables | Setup |
| --- | --- | --- |
| Bluesky | `BLUESKY_IDENTIFIER`, `BLUESKY_APP_PASSWORD` | Use a Bluesky-hosted account handle and generate an app password. [Bluesky posts guide](https://bsky.network/docs/about-bluesky-content/posts/) |
| Mastodon | `MASTODON_BASE_URL`, `MASTODON_ACCESS_TOKEN` | Use your instance's HTTPS URL and a user token with the `write:statuses` scope. [Statuses API](https://docs.joinmastodon.org/methods/statuses/#create) |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL` | Create a bot with BotFather, grant it posting rights as an admin of your public channel, and set the channel's username. [Bot API](https://core.telegram.org/bots/api#sendmessage) |
| DEV Community | `DEV_API_KEY` | Create a key in DEV's account settings and send content appropriate for the community. [Forem API](https://developers.forem.com/api/v1) |
| WordPress.com | `WORDPRESS_SITE`, `WORDPRESS_ACCESS_TOKEN` | Set a site ID or domain and obtain an OAuth token for a user authorized to publish. Set the site to public for anonymous readers. [OAuth setup](https://developer.wordpress.com/docs/api/getting-started/), [post endpoint](https://developer.wordpress.com/docs/api/1.1/post/sites/$site/posts/new/) |

## Request

Send `POST /posting` with a JSON body containing only `message`. The message may contain up to 200 characters and must contain exactly one valid, explicitly written HTTP or HTTPS URL. Invalid requests return HTTP 422 before contacting any platform.

```bash
curl -X POST http://localhost:4000/posting \
  -H 'Content-Type: application/json' \
  -d '{"message":"Read the mobile development guide https://example.com/guide"}'
```

This request attempts to publish immediately on all configured platforms. Run the API on a trusted local interface because the endpoint has no caller authentication. After a timeout or incomplete provider response, check the destination before resending to avoid duplicate posts.

## Example response

This abbreviated example shows the HTTP 200 response format. The API returns an entry for each of the five platforms. The top-level `success` is true when at least one platform confirms publication. Successful results report the time in UTC. Public visibility is based on provider settings or metadata.

```json
{
  "success": true,
  "results": [
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@demo/123",
      "public_access": true,
      "date": "2026-11-17",
      "time": "12:30:00",
      "error": null
    },
    {
      "platform": "Telegram",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Platform returned HTTP 403."
    }
  ]
}
```

## Project structure

| Path | Responsibility |
| --- | --- |
| `app/api/` | Route, input validation, and response schema |
| `app/application/` | Concurrent publishing and per-platform failure handling |
| `app/domain/` | Message and post models and the publisher contract |
| `app/platforms/` | Platform API integrations |
| `app/config.py` | Environment configuration |
| `app/main.py` | Application setup and HTTP client lifecycle |
| `tests/` | Endpoint and platform contract tests |

## Tests

```bash
python -m unittest discover -s tests -v
```

The tests use HTTPX's mock transport to exercise the endpoint and all five provider adapters without publishing externally. See [the test run](test-run.txt) for validation, payload checks, partial failure, timeouts, and private site visibility. Live verification requires credentials for the configured platforms.
