import logging
import difflib
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends

from app.core.config import settings
from app.core.auth import get_current_client_id
from app.models.conversation import Conversation, FeedbackPayload
from app.services.ai_service import generate_reply, initialize_resources, close_resources, ingest_feedback

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("--- Starting Application ---")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    initialize_resources()
    yield
    # --- Shutdown ---
    logger.info("--- Shutting Down Application ---")
    close_resources()

app = FastAPI(lifespan=lifespan)

@app.post("/generate-reply")
async def get_reply(
    conversation: Conversation,
    client_id: str = Depends(get_current_client_id)
):
    if not conversation.messages:
        raise HTTPException(status_code=400, detail="Conversation history cannot be empty.")

    # Assign the client_id from the token to the conversation
    conversation.client_id = client_id

    try:
        reply = await generate_reply(conversation)
        return {"reply": reply}
    except Exception as e:
        logger.error(f"An error occurred while generating reply: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")

@app.post("/feedback")
async def receive_feedback(
    payload: FeedbackPayload,
    background_tasks: BackgroundTasks,
    client_id: str = Depends(get_current_client_id)
):
    """
    Receives feedback on a generated reply to improve future suggestions.
    """
    logger.info(f"Received feedback for conversation {payload.conversation_id} from client {client_id}")

    # Assign the client_id from the token to the payload
    payload.client_id = client_id

    if payload.was_edited:
        diff = difflib.unified_diff(
            payload.original_draft.splitlines(keepends=True),
            payload.final_sent_message.splitlines(keepends=True),
            fromfile='original',
            tofile='final',
        )
        logger.info("Reply was edited. Diff:\n" + ''.join(diff))

    # Process the feedback in the background
    background_tasks.add_task(ingest_feedback, payload)

    return {"status": "Feedback received and is being processed."}

@app.get("/")
def read_root():
    return {"message": "Service is running."}

@app.get("/health")
def health_check():
    return {"status": "ok"}
