from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api.routes import router
from app.application.publish_message import PublishMessage
from app.config import Settings
from app.platforms.factory import build_publishers


def create_app(
    settings: Settings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = settings if settings is not None else Settings()
        async with httpx.AsyncClient(
            timeout=10,
            transport=transport,
            headers={"User-Agent": "automated-posting/1.0"},
        ) as client:
            app.state.publish_message = PublishMessage(build_publishers(client, config))
            yield

    app = FastAPI(title="Automated Multi-Platform Posting", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
