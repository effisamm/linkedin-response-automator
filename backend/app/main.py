import logging
import difflib
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.auth import get_current_client_id
from app.models.conversation import Conversation, FeedbackPayload
from app.services.ai_service import generate_reply, initialize_resources, close_resources, ingest_feedback

# Setup JSON logging
setup_logging()
logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request ID tracking.
    Generates a unique request ID (first 8 chars of UUID4) for each request
    and adds it to response headers.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        # Store in request state for use in handlers
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("--- Starting Application ---", extra={"environment": settings.ENVIRONMENT})
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    initialize_resources()
    yield
    # --- Shutdown ---
    logger.info("--- Shutting Down Application ---")
    close_resources()

app = FastAPI(lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)

@app.post("/generate-reply")
async def get_reply(
    conversation: Conversation,
    client_id: str = Depends(get_current_client_id),
    request: Request = None
):
    if not conversation.messages:
        raise HTTPException(status_code=400, detail="Conversation history cannot be empty.")

    # Assign the client_id from the token to the conversation
    conversation.client_id = client_id
    request_id = getattr(request.state, 'request_id', None) if request else None

    try:
        reply = await generate_reply(conversation, request_id=request_id)
        return {"reply": reply}
    except Exception as e:
        logger.error(
            f"An error occurred while generating reply: {e}",
            extra={"client_id": client_id, "request_id": request_id},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="An internal error occurred.")

@app.post("/feedback")
async def receive_feedback(
    payload: FeedbackPayload,
    background_tasks: BackgroundTasks,
    client_id: str = Depends(get_current_client_id),
    request: Request = None
):
    """
    Receives feedback on a generated reply to improve future suggestions.
    """
    request_id = getattr(request.state, 'request_id', None) if request else None
    logger.info(
        f"Received feedback for conversation {payload.conversation_id}",
        extra={
            "client_id": client_id,
            "conversation_id": payload.conversation_id,
            "request_id": request_id
        }
    )

    # Assign the client_id from the token to the payload
    payload.client_id = client_id

    if payload.was_edited:
        diff = difflib.unified_diff(
            payload.original_draft.splitlines(keepends=True),
            payload.final_sent_message.splitlines(keepends=True),
            fromfile='original',
            tofile='final',
        )
        diff_text = ''.join(diff)
        logger.info(
            "Reply was edited",
            extra={
                "client_id": client_id,
                "conversation_id": payload.conversation_id,
                "request_id": request_id,
                "diff": diff_text
            }
        )

    # Process the feedback in the background
    background_tasks.add_task(ingest_feedback, payload)

    return {"status": "Feedback received and is being processed."}

@app.get("/")
def read_root():
    return {"message": "Service is running."}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/clients")
def get_clients():
    """
    Returns a list of available clients (public endpoint, no auth required).
    """
    from app.services.ai_service import client_configs
    
    if not client_configs:
        return {"clients": []}
    
    clients = list(client_configs.keys())
    logger.info(
        "Clients retrieved",
        extra={"available_clients": clients}
    )
    return {"clients": clients}