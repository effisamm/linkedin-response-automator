from pydantic_settings import BaseSettings
from pydantic import SecretStr, Field
from pathlib import Path
from typing import Dict
import json

class Settings(BaseSettings):
    # --- Application ---
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")

    # --- AI Service ---
    EMBEDDING_MODEL_NAME: str = Field("all-MiniLM-L6-v2", env="EMBEDDING_MODEL_NAME")
    LLM_MODEL_NAME: str = "claude-sonnet-4-20250514"

    # --- API Keys ---
    ANTHROPIC_API_KEY: SecretStr = Field(..., env="ANTHROPIC_API_KEY")
    API_KEYS: Dict[str, str] = Field(default_factory=dict, env="API_KEYS")  # Expecting a JSON string in the environment variable

    # --- Data Paths ---
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DATA_PATH: Path = BASE_DIR / "data/conversations.json"
    CSV_DATA_PATH: Path = BASE_DIR / "data/linkedin_conversations.csv"
    CHROMADB_PATH: Path = BASE_DIR / "data/chroma_db"
    CHROMADB_COLLECTION_NAME: str = Field("linkedin_conversations", env="CHROMADB_COLLECTION_NAME")
    CLIENT_CONFIG_PATH: Path = BASE_DIR / "data/client_configs.json"
    CHROMADB_MODE: str = Field("embedded", env="CHROMADB_MODE")
    CHROMADB_HOST: str = Field("localhost", env="CHROMADB_HOST")
    CHROMADB_PORT: int = Field(8001, env="CHROMADB_PORT")

    # --- Rate Limiting ---
    RATE_LIMIT_PER_MINUTE: str = Field("20/minute", env="RATE_LIMIT_PER_MINUTE")
    EMBEDDING_WORKERS: int = Field(4, env="EMBEDDING_WORKERS")
    LLM_TIMEOUT_SECONDS: float = Field(30.0, env="LLM_TIMEOUT_SECONDS")
    RAG_CACHE_SIZE: int = Field(512, env="RAG_CACHE_SIZE")

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> any:
            if field_name == 'API_KEYS':
                return json.loads(raw_val)
            return raw_val

# Instantiate the settings
settings = Settings()
