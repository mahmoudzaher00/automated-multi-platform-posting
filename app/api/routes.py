from fastapi import APIRouter, Request

from app.api.schemas import PlatformResponse, PostingRequest, PostingResponse
from app.application.publish_message import PublishMessage

router = APIRouter()


@router.post("/posting", response_model=PostingResponse)
async def post_message(body: PostingRequest, request: Request) -> PostingResponse:
    publisher: PublishMessage = request.app.state.publish_message
    results = await publisher.execute(body.to_message())
    return PostingResponse(
        success=any(result.post is not None for result in results),
        results=[PlatformResponse.from_result(result) for result in results],
    )
