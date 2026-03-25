# Setup and Configuration Guide

Complete setup instructions for local development, Docker deployment, data ingestion, and Chrome extension configuration.

## Environment Variables

All configuration is managed through environment variables loaded from `backend/.env` at startup.

### Core Application Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ENVIRONMENT` | Deployment environment | `development` | `development`, `production` |
| `LOG_LEVEL` | Logging verbosity | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### API Authentication

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `API_KEYS` | JSON object mapping client IDs to API keys | Required | `'{"default": "sk_1234567890", "client2": "sk_0987654321"}'` |

**Important**: Must be valid JSON. Use single quotes around the entire JSON object when setting in shell.

### Anthropic API

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude access | Required | `sk-ant-v0-1a2b3c4d5e6f7g8h...` |

Get your API key from [api.anthropic.com](https://api.anthropic.com)

### AI Models

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `EMBEDDING_MODEL_NAME` | Sentence Transformers model for embeddings | `all-MiniLM-L6-v2` | Any Hugging Face model ID |
| `LLM_MODEL_NAME` | Claude model for reply generation | `claude-sonnet-4-20250514` | `claude-sonnet-4-20250514` |

### Data Paths

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `CSV_DATA_PATH` | Path to conversation CSV for ingestion | `backend/data/sample_conversations.csv` | `/app/data/conversations.csv` |
| `CHROMADB_COLLECTION_NAME` | Default ChromaDB collection name | `linkedin_conversations` | `linkedin_conversations` |
| `CLIENT_CONFIG_PATH` | Path to client configuration JSON | `backend/data/client_configs.json` | `/app/data/client_configs.json` |

### Example .env File

```bash
# Application
ENVIRONMENT=development
LOG_LEVEL=INFO

# API Keys
ANTHROPIC_API_KEY=sk-ant-v0-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
API_KEYS='{"default": "dev_key_12345", "client2": "dev_key_67890"}'

# Models
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
LLM_MODEL_NAME=claude-sonnet-4-20250514

# Data Paths (optional, use defaults if not set)
# CSV_DATA_PATH=/app/data/sample_conversations.csv
# CHROMADB_COLLECTION_NAME=linkedin_conversations
# CLIENT_CONFIG_PATH=/app/data/client_configs.json
```

## Local Development with Uvicorn

### Prerequisites

- Python 3.11 or higher
- pip or uv package manager
- Virtual environment

### Setup Steps

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment**:
   ```bash
   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows PowerShell
   python -m venv venv
   venv\Scripts\Activate.ps1

   # Windows Command Prompt
   python -m venv venv
   venv\Scripts\activate.bat
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Create .env file** in `backend/`:
   ```bash
   ENVIRONMENT=development
   LOG_LEVEL=DEBUG
   ANTHROPIC_API_KEY=sk-ant-...
   API_KEYS='{"default": "dev_key"}'
   ```

5. **Run development server**:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

   The `--reload` flag enables auto-restart on file changes.

6. **Access the API**:
   - OpenAPI docs: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

### Logs

In development mode with `LOG_LEVEL=DEBUG`, you'll see structured JSON logs in stdout:

```json
{"timestamp": "2026-03-24T10:30:45.123Z", "level": "DEBUG", "logger": "app.main", "message": "--- Starting Application ---", "environment": "development"}
```

## Docker Deployment

### Building the Image

```bash
cd backend

# Build image (takes ~5-10 minutes on first build due to model downloads)
docker build -t linkedin-automator:latest .

# Optional: tag for registry
docker tag linkedin-automator:latest myregistry/linkedin-automator:latest
```

### Running the Container

**Basic run with environment variables**:

```bash
docker run -d \
  --name linkedin-automator \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e API_KEYS='{"default": "prod_key"}' \
  -e ENVIRONMENT=production \
  -e LOG_LEVEL=INFO \
  linkedin-automator:latest
```

**Production run with persistent volume**:

```bash
# Create volume (one-time)
docker volume create linkedin-automator-data

# Run container with volume
docker run -d \
  --name linkedin-automator \
  -p 8000:8000 \
  -v linkedin-automator-data:/app/data \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e API_KEYS='{"default": "prod_key"}' \
  -e ENVIRONMENT=production \
  -e LOG_LEVEL=INFO \
  -e CHROMADB_PATH=/app/data/chroma_db \
  --health-cmd="curl -f http://localhost:8000/health || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-start-period=20s \
  linkedin-automator:latest
```

**Using volume mount (local directory)**:

```bash
docker run -d \
  --name linkedin-automator \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e API_KEYS='{"default": "prod_key"}' \
  linkedin-automator:latest
```

Windows (PowerShell):
```powershell
docker run -d `
  --name linkedin-automator `
  -p 8000:8000 `
  -v C:\data:/app/data `
  -e ANTHROPIC_API_KEY=sk-ant-... `
  -e API_KEYS='{"default": "prod_key"}' `
  linkedin-automator:latest
```

### Managing Container

```bash
# Check status
docker ps -a --filter name=linkedin-automator

# View logs
docker logs -f linkedin-automator

# Check health
docker ps --filter name=linkedin-automator --format "{{.Status}}"

# Stop container
docker stop linkedin-automator

# Start container
docker start linkedin-automator

# Remove container
docker rm -f linkedin-automator

# View container details
docker inspect linkedin-automator
```

### Multi-Stage Build Details

The provided Dockerfile uses multi-stage builds for optimization:

**Stage 1 - Builder**:
- Uses `python:3.11-slim`
- Installs all Python dependencies to `/install`
- No application code included

**Stage 2 - Runner**:
- Uses `python:3.11-slim` (minimal base)
- Copies only dependencies from builder
- Runs as non-root user `appuser` (UID 1000)
- Includes HEALTHCHECK
- Includes VOLUME mount point

This results in ~30-40% smaller final image compared to single-stage builds.

## Data Ingestion

ChromaDB requires vectorized conversation examples to power the RAG system. Use the ingestion script to populate the database.

### Ingestion Script

Located at `backend/scripts/ingest_data.py`

```bash
cd backend

# Ingest data for default client
python scripts/ingest_data.py --client-id default

# Ingest data for specific client
python scripts/ingest_data.py --client-id client2

# Help
python scripts/ingest_data.py --help
```

### CSV Format

The ingestion script expects `backend/data/sample_conversations.csv` with the following format:

```csv
messages
"[{'sender': 'Alice', 'text': 'Hi there!'}, {'sender': 'Bob', 'text': 'Hey! How are you?'}]"
"[{'sender': 'Charlie', 'text': 'Quick question...'}, {'sender': 'Diana', 'text': 'Sure, what is it?'}]"
```

- Each row is one conversation
- `messages` column contains JSON array of message objects
- Each message has `sender` (string) and `text` (string) fields

### Process

1. **Reads** CSV file from `CSV_DATA_PATH`
2. **Encodes** each conversation using Sentence Transformers embedding model
3. **Stores** in ChromaDB collection named in `client_configs.json`
4. **Skips** duplicate documents (by ID)
5. **Reports** statistics (processed, added, skipped)

### Example Output

```
{"timestamp": "2026-03-24T10:30:45.123Z", "level": "INFO", "logger": "scripts.ingest_data", "message": "Starting data ingestion", "client_id": "default"}
{"timestamp": "2026-03-24T10:30:45.234Z", "level": "INFO", "logger": "scripts.ingest_data", "message": "Connected to ChromaDB", "client_id": "default", "collection_name": "linkedin_conversations"}
...
{"timestamp": "2026-03-24T10:31:02.456Z", "level": "INFO", "logger": "scripts.ingest_data", "message": "Data ingestion complete", "client_id": "default", "total_processed": 1000, "total_added": 987, "collection_count": 987}
```

### Batch Processing

The ingestion script processes CSV in batches of 100 rows by default for memory efficiency:

```bash
# Edit batch size in ingest_data.py if needed
batch_generator = process_csv_in_batches(settings.CSV_DATA_PATH, batch_size=100)
```

## Loading Chrome Extension

The Chrome extension (`chrome-extension/`) provides the user-facing interface for generating and editing LinkedIn replies.

### Requirements

- Google Chrome or Chromium-based browser (Edge, Brave, etc.)
- Backend service running and accessible
- Extension configured with API endpoint and client token

### Loading Unpacked Extension

1. **Open Chrome Extensions page**:
   - URL: `chrome://extensions/`
   - Or: Menu → More Tools → Extensions

2. **Enable Developer Mode**:
   - Toggle switch in top-right corner
   - You'll see new buttons appear: "Load unpacked", "Pack extension", etc.

3. **Load the extension**:
   - Click "Load unpacked"
   - Navigate to `chrome-extension/` directory
   - Click "Select Folder"

4. **Verify installation**:
   - Extension appears in the list
   - Icon appears in Chrome toolbar (puzzle piece)
   - ID is displayed (e.g., `jkhfsdklfjh234234`)

5. **Pin to toolbar** (optional):
   - Click extension icon in toolbar
   - Right-click on extension card
   - Select "Pin to toolbar" for quick access

### Configuring Extension

The extension needs to know where to find your backend API and which client token to use.

#### Via Popup Configuration

1. Click extension icon in toolbar
2. Click "Settings" button
3. Enter configuration:
   - **API Endpoint**: `http://localhost:8000` (development) or `https://api.example.com` (production)
   - **Client ID**: Name of your client (e.g., `default`, `client2`)
   - **API Key**: Bearer token from `API_KEYS` environment variable

4. Click "Save"

#### Via popup.js Code

Edit `chrome-extension/popup.js` to hardcode configuration:

```javascript
const DEFAULT_CONFIG = {
  apiEndpoint: 'http://localhost:8000',
  clientId: 'default',
  apiKey: 'dev_key_12345'
};
```

#### Via Chrome DevTools

1. Open Chrome DevTools (`F12` or `Ctrl+Shift+I`)
2. Go to Console tab
3. Run:
   ```javascript
   chrome.storage.sync.set({
     apiEndpoint: 'http://localhost:8000',
     clientId: 'default',
     apiKey: 'dev_key_12345'
   }, () => console.log('Settings saved'));
   ```

### Testing the Extension

1. **Open LinkedIn** in a new tab
2. **Open a message thread** (click on a conversation)
3. **Scroll to reply compose box** at bottom
4. **Click extension icon** in toolbar
5. You should see:
   - "Generate Reply" button appears in compose box
   - Generated reply suggested in dropdown
   - Option to insert reply or edit it

### Troubleshooting

**Extension doesn't appear**:
- Verify it's loaded in `chrome://extensions/`
- Refresh LinkedIn page (`F5`)
- Check that extension is enabled (toggle switch)

**"Generate Reply" button not appearing**:
- Check browser console for errors (`F12` → Console)
- Verify backend is running: `curl http://localhost:8000/health`
- Check network tab to see API requests

**"Failed to fetch" errors**:
- Verify API endpoint is correct in extension settings
- Check CORS settings in backend
- Ensure API key is valid in `API_KEYS` environment variable

**"401 Unauthorized" errors**:
- Verify API key matches one in `API_KEYS` environment variable
- Check `Authorization: Bearer <key>` header is sent
- Review backend logs: `docker logs linkedin-automator`

## Configuring Extension Popup

The extension popup UI is defined in `chrome-extension/popup.html`, styled with `popup.css`, and controlled by `popup.js`.

### Popup Layout

The popup contains:

1. **Status Display**: Shows current connection status and configuration
2. **Settings Form**: Fields for API endpoint, client ID, and API key
3. **Save Button**: Persists settings to Chrome's sync storage
4. **Clear Button**: Resets to defaults

### Customizing Popup

**popup.html**: HTML structure
```html
<div id="settings">
  <input type="text" id="apiEndpoint" placeholder="API Endpoint">
  <input type="text" id="clientId" placeholder="Client ID">
  <input type="password" id="apiKey" placeholder="API Key">
  <button id="saveBtn">Save Settings</button>
</div>
```

**popup.css**: Visual styling
```css
#settings {
  width: 300px;
  padding: 15px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
}

#apiEndpoint, #clientId, #apiKey {
  width: 100%;
  margin: 5px 0;
  padding: 8px;
}
```

**popup.js**: Load/save functionality
```javascript
// Load settings on popup open
chrome.storage.sync.get(['apiEndpoint', 'clientId', 'apiKey'], (result) => {
  document.getElementById('apiEndpoint').value = result.apiEndpoint || '';
  document.getElementById('clientId').value = result.clientId || '';
  document.getElementById('apiKey').value = result.apiKey || '';
});

// Save settings on button click
document.getElementById('saveBtn').addEventListener('click', () => {
  chrome.storage.sync.set({
    apiEndpoint: document.getElementById('apiEndpoint').value,
    clientId: document.getElementById('clientId').value,
    apiKey: document.getElementById('apiKey').value
  });
});
```

### Content Script Integration

The `content_script.js` runs on LinkedIn pages and:
1. Detects message compose boxes
2. Injects "Generate Reply" button
3. Calls extension popup for settings
4. Makes API requests to backend

## Adding a New Client

To support multiple LinkedIn accounts with isolated configurations and data:

### Step 1: Generate API Key

Create a unique API key for the new client. Use a secure random generator:

```bash
# macOS/Linux
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"

# Output example: 4f3e7d2a1b9c5e8f3a2d1c4b7e9f3a2b
```

### Step 2: Update Environment Variable

Add new key to `API_KEYS` environment variable:

```bash
# Current
API_KEYS='{"default": "dev_key_12345"}'

# Updated
API_KEYS='{"default": "dev_key_12345", "client_new": "4f3e7d2a1b9c5e8f3a2d1c4b7e9f3a2b"}'
```

For Docker, update at runtime or in compose file:

```bash
docker run -d \
  -e API_KEYS='{"default": "...", "client_new": "..."}' \
  linkedin-automator:latest
```

### Step 3: Create Client Configuration

Edit `backend/data/client_configs.json`:

```json
{
  "default": {
    "collection_name": "linkedin_conversations",
    "tone_instructions": "Professional but conversational",
    "company_context": "B2B SaaS sales"
  },
  "client_new": {
    "collection_name": "linkedin_conversations_client_new",
    "tone_instructions": "Friendly and personable",
    "company_context": "Recruiting agency specializing in tech"
  }
}
```

Fields:
- `collection_name`: ChromaDB collection for this client (must be unique)
- `tone_instructions`: How the AI should adjust reply tone
- `company_context`: Business context for better replies

### Step 4: Ingest Client Data

Create or provide CSV file for the new client at `backend/data/sample_conversations_client_new.csv`.

Update `backend/.env` if using different CSV path, or run ingestion:

```bash
cd backend
python scripts/ingest_data.py --client-id client_new
```

Check logs for success:
```json
{"message": "Data ingestion complete", "client_id": "client_new", "total_added": 1000}
```

### Step 5: Configure Extension

For each Chrome browser using this client, configure in extension:

1. Click extension icon
2. Enter:
   - **API Endpoint**: Backend URL
   - **Client ID**: `client_new`
   - **API Key**: The generated key from Step 1

3. Click Save

### Step 6: Test

1. Open LinkedIn in the browser
2. Click extension icon
3. Open a message thread
4. Should see "Generate Reply" button
5. Click to generate a reply
6. Verify reply uses client_new's tone and context

### Multi-Client Architecture

Each client has:
- **Isolated API token** for authentication
- **Separate ChromaDB collection** for training data
- **Custom configuration** for tone and context
- **Independent feedback loop** for learning

Request flow for `client_new`:

```
Chrome Extension
   ↓
   POST /generate-reply
   Authorization: Bearer 4f3e7d2a1b9c5e8f...
   ↓
Backend Authenticates (checks API_KEYS)
   ↓
Query ChromaDB collection: linkedin_conversations_client_new
   ↓
Load client_new config: tone_instructions, company_context
   ↓
Generate reply using client_new's configuration
   ↓
Return to extension
```

Clients never see each other's data or configuration.

## Troubleshooting

### "API key not found" error

**Problem**: Backend rejects requests from extension

**Solution**:
1. Verify API key in `API_KEYS` environment variable matches extension setting
2. Restart backend to reload environment
3. Check logs: `docker logs linkedin-automator | grep -i auth`

### "Collection not found" error

**Problem**: Client configuration references non-existent ChromaDB collection

**Solution**:
1. Verify collection name in `client_configs.json` matches ChromaDB collection
2. Run ingestion script to create collection:
   ```bash
   python scripts/ingest_data.py --client-id <client_id>
   ```
3. Verify ChromaDB data directory has write permissions

### Models not downloading

**Problem**: First ingestion or startup is very slow, or fails

**Solution**:
1. Sentence Transformers model downloads on first use (~350MB)
2. Ensure sufficient disk space
3. Run with internet connection
4. Check logs for download progress

### Memory issues

**Problem**: Out of memory errors during ingestion

**Solution**:
1. Reduce batch size in `ingest_data.py`:
   ```bash
   batch_generator = process_csv_in_batches(settings.CSV_DATA_PATH, batch_size=50)
   ```
2. Ensure adequate RAM: recommended 4GB minimum, 8GB+ for large datasets
3. Close other applications

---

**Last Updated**: March 2026
