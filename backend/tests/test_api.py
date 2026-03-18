import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from app.main import app
from app.core.config import settings

# Fixture to mock resource initialization and shutdown for all tests
@pytest.fixture(autouse=True)
def mock_lifespan_events():
    with patch("app.main.initialize_resources"), patch("app.main.close_resources"):
        yield

# Fixture to provide a valid API key and associated client ID for tests
@pytest.fixture
def authenticated_client():
    test_api_key = "test_key_123"
    test_client_id = "test_client"
    with patch.dict(settings.API_KEYS, {test_api_key: test_client_id}):
        yield {"x-api-key": test_api_key}, test_client_id

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_generate_reply_no_api_key():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/generate-reply",
            json={"messages": [{"sender": "User", "text": "Hello"}]}
        )
        assert response.status_code == 422 # FastAPI's way of saying "Missing Header"

@pytest.mark.asyncio
@patch('app.services.ai_service.generate_reply', new_callable=AsyncMock)
async def test_generate_reply_success(mock_generate_reply, authenticated_client):
    headers, client_id = authenticated_client
    mock_generate_reply.return_value = "This is a mock reply."
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/generate-reply",
            json={"messages": [{"sender": "User", "text": "Hello"}]},
            headers=headers
        )
        assert response.status_code == 200
        assert response.json() == {"reply": "This is a mock reply."}
        # Verify that the client_id was correctly passed to the service layer
        mock_generate_reply.assert_awaited_once()
        call_args = mock_generate_reply.call_args[0][0] # Get the 'conversation' argument
        assert call_args.client_id == client_id

@pytest.mark.asyncio
async def test_feedback_invalid_api_key():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/feedback",
            json={
                "conversation_id": "test-convo-123",
                "original_draft": "Draft.",
                "final_sent_message": "Final.",
                "was_edited": True,
                "conversation_context": {"messages": [{"sender": "User", "text": "Context."}]}
            },
            headers={"x-api-key": "invalid_key"}
        )
        assert response.status_code == 401

@pytest.mark.asyncio
@patch('app.services.ai_service.ingest_feedback', new_callable=AsyncMock)
async def test_feedback_success(mock_ingest_feedback, authenticated_client):
    headers, client_id = authenticated_client
    feedback_payload = {
        "conversation_id": "test-convo-123",
        "original_draft": "Draft.",
        "final_sent_message": "Final.",
        "was_edited": True,
        "conversation_context": {"messages": [{"sender": "User", "text": "Context."}]}
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/feedback", json=feedback_payload, headers=headers)
        assert response.status_code == 200
        
        mock_ingest_feedback.assert_awaited_once()
        call_args = mock_ingest_feedback.call_args[0][0] # Get the 'payload' argument
        assert call_args.client_id == client_id
