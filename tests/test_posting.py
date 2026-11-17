import json
import unittest
from contextlib import asynccontextmanager
from datetime import datetime
from urllib.parse import parse_qs

import httpx

from app.config import Settings
from app.main import create_app

LINK = "https://example.com/guide"
MESSAGE = f"📱 دليل التطبيق ({LINK})."
PUBLISHED_AT = "2026-11-17T12:30:00+00:00"


class PostingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.requests = []
        self.provider_failures = {}
        self.wordpress_private = False
        self.settings = Settings(
            _env_file=None,
            bluesky_identifier="demo.bsky.social",
            bluesky_app_password="test-app-password",
            mastodon_access_token="test-mastodon-token",
            telegram_bot_token="test-bot-token",
            telegram_channel="@demochannel",
            dev_api_key="test-dev-key",
            wordpress_site="123",
            wordpress_access_token="test-wordpress-token",
        )

    def provider(self, request):
        self.requests.append(request)
        host = request.url.host
        if host in self.provider_failures:
            failure = self.provider_failures[host]
            if isinstance(failure, int):
                return httpx.Response(failure, json={"error": "provider diagnostics"})
            raise failure

        match host, request.method, request.url.path.rsplit("/", 1)[-1]:
            case "bsky.social", "POST", "com.atproto.server.createSession":
                return httpx.Response(200, json={"did": "did:plc:demo", "accessJwt": "test-jwt"})
            case "bsky.social", "POST", "com.atproto.repo.createRecord":
                return httpx.Response(
                    200, json={"uri": "at://did:plc:demo/app.bsky.feed.post/demo"}
                )
            case "mastodon.social", "POST", "statuses":
                return httpx.Response(200, json={
                    "url": "https://mastodon.social/@demo/123",
                    "visibility": "public",
                    "created_at": PUBLISHED_AT,
                })
            case "api.telegram.org", "POST", "sendMessage":
                return httpx.Response(200, json={
                    "ok": True,
                    "result": {
                        "message_id": 11,
                        "date": int(datetime.fromisoformat(PUBLISHED_AT).timestamp()),
                        "chat": {"type": "channel", "username": "demochannel"},
                    },
                })
            case "dev.to", "POST", "articles":
                return httpx.Response(201, json={
                    "url": "https://dev.to/demo/update",
                    "published_at": PUBLISHED_AT,
                })
            case "public-api.wordpress.com", "GET", "123":
                return httpx.Response(200, json={"is_private": self.wordpress_private})
            case "public-api.wordpress.com", "POST", "new":
                return httpx.Response(201, json={
                    "URL": "https://demo.wordpress.com/update/",
                    "status": "publish",
                    "date": "2026-11-17T14:30:00+02:00",
                })
        self.fail(f"Unexpected request to {request.method} {host}")

    @asynccontextmanager
    async def client(self, settings=None):
        app = create_app(settings or self.settings, httpx.MockTransport(self.provider))
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                yield client

    async def test_publishes_to_all_five_platforms(self):
        async with self.client() as client:
            response = await client.post("/posting", json={"message": MESSAGE})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        results = {result["platform"]: result for result in body["results"]}
        self.assertEqual(set(results), {"Bluesky", "Mastodon", "Telegram", "DEV Community", "WordPress.com"})
        for result in results.values():
            self.assertEqual(result["status"], "success")
            self.assertTrue(result["public_access"])
            self.assertIsNone(result["error"])
            if result["platform"] != "Bluesky":
                self.assertEqual(result["date"], "2026-11-17")
                self.assertEqual(result["time"], "12:30:00")

        self.assertEqual(results["Bluesky"]["posted_url"], "https://bsky.app/profile/did:plc:demo/post/demo")
        self.assertEqual(results["Telegram"]["posted_url"], "https://t.me/demochannel/11")
        requests = {request.url.path.rsplit("/", 1)[-1]: request for request in self.requests}
        bluesky_request = requests["com.atproto.repo.createRecord"]
        record = json.loads(bluesky_request.content)["record"]
        bluesky_date, bluesky_time = record["createdAt"].split("T", 1)
        self.assertEqual(results["Bluesky"]["date"], bluesky_date)
        self.assertEqual(results["Bluesky"]["time"], bluesky_time[:8])
        facet = record["facets"][0]
        start, end = facet["index"]["byteStart"], facet["index"]["byteEnd"]
        self.assertEqual(record["text"].encode()[start:end].decode(), LINK)
        self.assertEqual(facet["features"][0]["uri"], LINK)
        self.assertEqual(bluesky_request.headers["Authorization"], "Bearer test-jwt")

        mastodon_form = parse_qs(requests["statuses"].content.decode())
        self.assertEqual(mastodon_form, {"status": [MESSAGE], "visibility": ["public"]})
        self.assertEqual(json.loads(requests["sendMessage"].content)["chat_id"], "@demochannel")
        self.assertTrue(json.loads(requests["articles"].content)["article"]["published"])
        site_post = parse_qs(requests["new"].content.decode())
        self.assertEqual(site_post["status"], ["publish"])
        self.assertIn(f'<a href="{LINK}">{LINK}</a>', site_post["content"][0])

    async def test_keeps_other_platform_results_when_one_fails(self):
        self.provider_failures["api.telegram.org"] = 403
        async with self.client() as client:
            response = await client.post("/posting", json={"message": MESSAGE})
        body = response.json()

        self.assertTrue(body["success"])
        failures = [result for result in body["results"] if result["status"] == "failed"]
        self.assertEqual(failures, [{
            "platform": "Telegram",
            "status": "failed",
            "posted_url": None,
            "public_access": False,
            "date": None,
            "time": None,
            "error": "Platform returned HTTP 403.",
        }])

    async def test_handles_upstream_timeout(self):
        self.provider_failures["mastodon.social"] = httpx.ReadTimeout("request timed out")
        async with self.client() as client:
            response = await client.post("/posting", json={"message": MESSAGE})
        body = response.json()

        self.assertTrue(body["success"])
        self.assertIn("timed out", body["results"][1]["error"])

    async def test_reports_private_wordpress_site(self):
        self.wordpress_private = True
        async with self.client() as client:
            response = await client.post("/posting", json={"message": MESSAGE})
        body = response.json()

        wordpress = body["results"][-1]
        self.assertEqual(wordpress["status"], "success")
        self.assertFalse(wordpress["public_access"])

    async def test_reports_missing_credentials_without_network_requests(self):
        empty_settings = {
            key: "" for key in Settings.model_fields
        }
        async with self.client(Settings(_env_file=None, **empty_settings)) as client:
            response = await client.post("/posting", json={"message": MESSAGE})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(len(body["results"]), 5)
        self.assertTrue(all(result["status"] == "failed" for result in body["results"]))
        self.assertEqual(self.requests, [])

    async def test_accepts_exactly_200_characters(self):
        message = f"{'a' * (199 - len(LINK))} {LINK}"
        async with self.client() as client:
            response = await client.post("/posting", json={"message": message})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    async def test_rejects_invalid_messages_without_contacting_platforms(self):
        invalid = [
            {},
            {"message": 5},
            {"message": ""},
            {"message": "Missing a link"},
            {"message": f"{LINK} {LINK}"},
            {"message": "Invalid https://"},
            {"message": "Invalid https:///example.com"},
            {"message": "Invalid ftp://example.com"},
            {"message": "Invalid https://example.com:bad"},
            {"message": "Invalid https://user:password@example.com"},
            {"message": f"{'a' * (200 - len(LINK))} {LINK}"},
            {"message": MESSAGE, "platform": "Telegram"},
        ]
        async with self.client() as client:
            for body in invalid:
                with self.subTest(body=body):
                    response = await client.post("/posting", json=body)
                    self.assertEqual(response.status_code, 422)

        self.assertEqual(self.requests, [])
