# LinkedIn Response Automator

AI-powered LinkedIn reply generation using Retrieval Augmented Generation (RAG) with Claude. Automatically compose professional, contextually-aware responses to LinkedIn messages with a Chrome extension.

## Features

- **Intelligent Reply Generation**: Uses Claude 3 Sonnet to generate contextually appropriate LinkedIn responses
- **Retrieval Augmented Generation (RAG)**: Learns from historical conversations to generate personalized replies
- **Multi-Tenant Support**: Manage multiple LinkedIn accounts with isolated configurations and data
- **Conversation Stage Detection**: Automatically detects conversation stage (greeting, proposal, negotiation, etc.)
- **Feedback Loop**: Continuously improves suggestions based on user edits
- **JSON Logging**: Structured logging with request ID tracking for debugging and monitoring
- **Production-Ready**: Multi-stage Docker build, non-root user, health checks, volume persistence

## Architecture

**Frontend**: Chrome extension that intercepts LinkedIn conversations and integrates with the backend API

**Backend**: FastAPI service with:
- Vector database (ChromaDB) for storing and retrieving similar conversations
- Embedding model (Sentence Transformers) for semantic search
- LLM integration (Anthropic Claude) for reply generation
- Multi-tenant isolation with per-client ChromaDB collections

## Prerequisites

- Python 3.11+
- Docker (for production deployment)
- Google Chrome browser
- Anthropic API key
- Internet connection

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/linkedin-response-automator.git
cd linkedin-response-automator
```

### 2. Configure Environment

Create `backend/.env`:

```bash
ENVIRONMENT=development
LOG_LEVEL=INFO
ANTHROPIC_API_KEY=sk-ant-...
API_KEYS='{"client1": "key1", "client2": "key2"}'
```

See [docs/setup.md](docs/setup.md#environment-variables) for all available variables.

### 3. Local Development (Uvicorn)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at `http://localhost:8000`

### 4. Docker Deployment

```bash
cd backend
docker build -t linkedin-automator .
docker run -d \
  --name linkedin-automator \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e API_KEYS='{"client1": "key1"}' \
  linkedin-automator
```

### 5. Load Chrome Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Navigate to `chrome-extension/` directory
5. Extension now appears in toolbar

See [docs/setup.md#loading-chrome-extension](docs/setup.md#loading-chrome-extension) for detailed instructions.

### 6. Ingest Sample Data

```bash
cd backend
python scripts/ingest_data.py --client-id default
```

This loads sample conversations into ChromaDB for the default client, enabling the RAG system to retrieve similar conversations.

## API Endpoints

### Generate Reply
```http
POST /generate-reply
Authorization: Bearer <client_token>
Content-Type: application/json

{
  "messages": [
    {"sender": "Sarah Chen", "text": "Hi! Are you available for a quick call?"},
    {"sender": "You", "text": "I'd be happy to chat. When works best?"}
  ]
}

Response:
{
  "reply": "Tuesday or Wednesday afternoon would work great for me. Does 2 PM work?"
}
```

### Submit Feedback
```http
POST /feedback
Authorization: Bearer <client_token>
Content-Type: application/json

{
  "conversation_id": "conv_123",
  "original_draft": "Sure, let's chat",
  "final_sent_message": "Absolutely! I'd love to discuss this further.",
  "was_edited": true,
  "conversation_context": {
    "messages": [{"sender": "Client", "text": "..."}]
  }
}

Response:
{
  "status": "Feedback received and is being processed."
}
```

### Health Check
```http
GET /health

Response:
{
  "status": "ok"
}
```

## Documentation

- **[Setup Guide](docs/setup.md)**: Environment variables, local development, Docker deployment, data ingestion, extension configuration
- **[Architecture](docs/architecture.md)**: System design, RAG pipeline, multi-tenant model, request flow diagrams

## Project Structure

```
.
├── backend/                          # FastAPI backend service
│   ├── app/
│   │   ├── core/
│   │   │   ├── auth.py              # API key authentication
│   │   │   ├── config.py            # Settings from environment
│   │   │   └── logging_config.py    # JSON logging setup
│   │   ├── models/
│   │   │   └── conversation.py      # Data models
│   │   ├── services/
│   │   │   └── ai_service.py        # RAG and reply generation
│   │   └── main.py                  # FastAPI app entry point
│   ├── data/
│   │   ├── client_configs.json      # Per-client settings
│   │   ├── sample_conversations.csv # Training data
│   │   └── chroma_db/               # Vector database (volume-persisted)
│   ├── scripts/
│   │   └── ingest_data.py           # CSV → ChromaDB ingestion
│   ├── tests/                        # Unit and integration tests
│   ├── requirements.txt              # Python dependencies
│   └── Dockerfile                    # Production-ready multi-stage build
├── chrome-extension/                 # Chrome extension frontend
│   ├── manifest.json                # Extension metadata
│   ├── popup.html/css/js            # Configuration UI
│   ├── content_script.js            # LinkedIn page integration
│   └── background.js                # Event handling
└── docs/
    ├── setup.md                      # Setup and configuration guide
    └── architecture.md               # System architecture and design
```

## Development

### Running Tests

```bash
cd backend
pytest tests/ -v
```

### Local ChromaDB

ChromaDB persists to `backend/data/chroma_db/` when running locally. Delete this directory to reset:

```bash
rm -rf backend/data/chroma_db/
```

### Logs

With JSON logging enabled, all logs are structured JSON for easy parsing and monitoring:

```json
{"timestamp": "2026-03-24T10:30:45.123Z", "level": "INFO", "logger": "app.services.ai_service", "message": "Generating reply", "client_id": "default", "stage": "api_call_complete", "request_id": "a1b2c3d4"}
```

## Configuration

### Per-Client Settings

Edit `backend/data/client_configs.json` to customize behavior per client:

```json
{
  "default": {
    "collection_name": "linkedin_conversations",
    "tone_instructions": "Professional but conversational",
    "company_context": "B2B SaaS sales"
  }
}
```

### API Authentication

Clients authenticate via bearer token. Set `API_KEYS` environment variable with JSON:

```bash
API_KEYS='{"client1": "super_secret_key_1", "client2": "super_secret_key_2"}'
```

See [docs/setup.md#adding-a-new-client](docs/setup.md#adding-a-new-client) for step-by-step instructions.

## Troubleshooting

### Extension not working
- Check browser console for errors (`F12` → Console)
- Verify extension is enabled in `chrome://extensions/`
- Ensure backend is running and accessible
- Check network tab in DevTools to see API requests

### No replies generated
- Verify API key is set and valid
- Check backend logs: `docker logs linkedin-automator` or console output
- Ensure data has been ingested: `python scripts/ingest_data.py --client-id default`
- Check `/health` endpoint returns `{"status": "ok"}`

### ChromaDB errors
- Ensure `/app/data` volume has write permissions
- Docker: `chmod 777 backend/data/chroma_db/` (locally)
- Check available disk space

## Performance

- **Reply generation**: ~2-5 seconds (includes embedding + retrieval + LLM call)
- **Vector similarity search**: ~500ms
- **LLM inference**: ~1-3 seconds (Claude 3 Sonnet)
- **Concurrent requests**: Scales horizontally with multiple uvicorn workers (2 by default in Docker)

## Security

- Non-root Docker container (UID 1000)
- Bearer token authentication for all API endpoints
- Per-client data isolation with ChromaDB collections
- Environment-based secrets (no hardcoding)
- CORS disabled by default

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

For issues, questions, or suggestions, please open a GitHub issue or contact the development team.

---

**Last Updated**: March 2026  
**Status**: Production Ready