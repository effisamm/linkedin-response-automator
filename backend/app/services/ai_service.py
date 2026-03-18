import asyncio
import json
import logging
from concurrent.futures import ProcessPoolExecutor
import chromadb
from chromadb.api.client import Client
from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer
from async_lru import alru_cache
from fastapi.concurrency import run_in_threadpool
import anthropic
from typing import List, Dict

from app.core.config import settings
from app.models.conversation import Conversation, ConversationStage, Message, FeedbackPayload

logger = logging.getLogger(__name__)

# --- Global Variables ---
collections: Dict[str, Collection] = {}
executor: ProcessPoolExecutor | None = None
anthropic_client: anthropic.AsyncAnthropic | None = None
client_configs: Dict[str, Dict] = {}

# --- CPU-Bound Task ---
def encode_text_task(text: str, model_name: str) -> list[list[float]]:
    process_local_model = SentenceTransformer(model_name)
    return process_local_model.encode([text]).tolist()

# --- Lifespan Functions ---
def initialize_resources():
    global collections, executor, anthropic_client, client_configs
    
    logger.info("Initializing resources...")
    logger.info(f"Using LLM: {settings.LLM_MODEL_NAME}")
    logger.info(f"Using Embedding Model: {settings.EMBEDDING_MODEL_NAME}")
    
    executor = ProcessPoolExecutor()
    
    with open(settings.CLIENT_CONFIG_PATH, 'r') as f:
        client_configs = json.load(f)
    
    # Ensure the ChromaDB directory exists
    settings.CHROMADB_PATH.mkdir(parents=True, exist_ok=True)
    
    client: Client = chromadb.PersistentClient(path=str(settings.CHROMADB_PATH))
    
    for client_id, config in client_configs.items():
        collection_name = config['collection_name']
        collections[client_id] = client.get_or_create_collection(name=collection_name)
        logger.info(f"ChromaDB collection for '{client_id}' ('{collection_name}') loaded with {collections[client_id].count()} documents.")

    try:
        anthropic_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY.get_secret_value())
        # Perform a simple test call to validate the API key
        asyncio.run(anthropic_client.messages.create(
            model=settings.LLM_MODEL_NAME,
            max_tokens=1,
            messages=[{"role": "user", "content": "test"}]
        ))
        logger.info("Anthropic client initialized and API key validated.")
    except anthropic.AuthenticationError as e:
        logger.error("--- ANTHROPIC AUTHENTICATION FAILED ---")
        logger.error("Could not authenticate with Anthropic. Please check your ANTHROPIC_API_KEY.")
        logger.error(f"Underlying error: {e}")
        raise SystemExit("Exiting due to Anthropic authentication failure.") from e
    except Exception as e:
        logger.error(f"An unexpected error occurred during Anthropic client initialization: {e}")
        raise

def close_resources():
    global executor
    if executor:
        logger.info("Shutting down process pool...")
        executor.shutdown()

# --- Feedback Ingestion ---
async def ingest_feedback(payload: FeedbackPayload):
    """
    Ingests user feedback into the vector database to improve future suggestions.
    """
    global collections, executor
    client_id = payload.client_id or "default"
    collection = collections.get(client_id)

    if not collection or not executor:
        print(f"Error: Resources not initialized for feedback ingestion for client '{client_id}'.")
        return

    print(f"Ingesting feedback for conversation {payload.conversation_id} for client '{client_id}'...")

    context_text = " ".join([msg.text for msg in payload.conversation_context.messages])
    full_document = f"{context_text} {payload.final_sent_message}"

    loop = asyncio.get_running_loop()
    embedding = await loop.run_in_executor(
        executor, encode_text_task, full_document, settings.EMBEDDING_MODEL_NAME
    )

    doc_id = f"feedback_{payload.conversation_id}"

    def db_upsert():
        collection.upsert(
            ids=[doc_id],
            embeddings=embedding,
            documents=[full_document],
            metadatas=[{"source": "feedback", "client_id": payload.client_id}]
        )

    await run_in_threadpool(db_upsert)
    print(f"Feedback document {doc_id} upserted into collection for '{client_id}'.")

    find_similar_conversations.cache_clear()
    print("Cleared find_similar_conversations cache.")

# --- Conversation Stage Detection ---
@alru_cache(maxsize=128)
async def detect_stage(messages: tuple[Message]) -> ConversationStage:
    """
    Detects the current stage of a conversation using the Claude API.
    The tuple conversion is necessary for caching since lists are not hashable.
    """
    if not anthropic_client:
        raise RuntimeError("Anthropic client not initialized.")

    conversation_text = "\n".join([f"{msg.sender}: {msg.text}" for msg in messages])

    valid_stages = [s.value for s in ConversationStage if s != ConversationStage.UNKNOWN]

    system_prompt = f"""You are a conversation analyst. Your task is to classify the current stage of a LinkedIn conversation.
Based on the last message, please classify the conversation into one of the following categories:
{', '.join(valid_stages)}.
Return only the category name.
"""

    user_prompt = f"Here is the conversation:\n{conversation_text}"

    try:
        response = await anthropic_client.messages.create(
            model=settings.LLM_MODEL_NAME,
            max_tokens=50,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        stage_str = response.content[0].text.strip().lower()
        return ConversationStage(stage_str)

    except (Exception, ValueError) as e:
        print(f"Error detecting conversation stage: {e}")
        return ConversationStage.UNKNOWN

# --- Async RAG Logic with Caching ---
@alru_cache(maxsize=128)
async def find_similar_conversations(query_text: str, client_id: str, n_results: int = 3) -> list[str]:
    global collections, executor
    collection = collections.get(client_id)
    if not collection or not executor:
        raise RuntimeError(f"Resources not initialized for client '{client_id}'.")

    loop = asyncio.get_running_loop()
    query_embedding = await loop.run_in_executor(
        executor, encode_text_task, query_text, settings.EMBEDDING_MODEL_NAME
    )

    def db_query():
        return collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )
    results = await run_in_threadpool(db_query)
    return results['documents'][0] if results and results['documents'] else []

async def generate_reply(conversation: Conversation) -> str:
    """
    Generates a reply using a RAG approach with the Claude API.
    """
    client_id = conversation.client_id or "default"
    client_config = client_configs.get(client_id, client_configs.get("default", {}))

    # 1. Get embeddings and context
    current_conversation_text = " ".join([msg.text for msg in conversation.messages])
    similar_examples = await find_similar_conversations(current_conversation_text, client_id=client_id, n_results=3)

    # 2. Construct prompt components
    examples_block = "\n---\n".join(similar_examples)
    thread_block = "\n".join([f"{msg.sender}: {msg.text}" for msg in conversation.messages])
    last_sender = conversation.messages[-1].sender

    # 3. Define the new system and user prompts
    system_prompt = f"""You are ghostwriting LinkedIn replies for a sales rep.
Rules: max 3 sentences, no bullet points, never open with affirmations
(Great/Sure/Absolutely), never mention AI, mirror examples' energy.
If prospect asked a question, answer it in the first sentence.
Tone: {client_config.get('tone_instructions', 'Default tone')}. Context: {client_config.get('company_context', 'Default context')}"""

    user_prompt = f"""== Historical examples ==
{examples_block}
== Current thread ==
{thread_block}
== Task ==
Write the rep's next reply to {last_sender}. Output only the message text."""

    try:
        if not anthropic_client:
            raise RuntimeError("Anthropic client not initialized.")
        
        message = await anthropic_client.messages.create(
            model=settings.LLM_MODEL_NAME,
            max_tokens=150,
            temperature=0.4,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )
        
        reply = message.content[0].text if message.content else "Sorry, I couldn't generate a reply."
        return reply

    except Exception as e:
        print(f"Error calling Anthropic API: {e}")
        raise
