from pydantic_settings import BaseSettings
from pydantic import SecretStr, Field
from pathlib import Path
from typing import Dict
import json

class Settings(BaseSettings):
    # --- Application ---
    ENVIRONMENT: str = "development"

    # --- AI Service ---
    EMBEDDING_MODEL_NAME: str = Field("all-MiniLM-L6-v2", env="EMBEDDING_MODEL_NAME")
    LLM_MODEL_NAME: str = "claude-3-5-sonnet-20240620"

    # --- API Keys ---
    ANTHROPIC_API_KEY: SecretStr
    API_KEYS: Dict[str, str] = Field(default_factory=dict)

    # --- Data Paths ---
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DATA_PATH: Path = BASE_DIR / "data/conversations.json"
    CSV_DATA_PATH: Path = BASE_DIR / "data/sample_conversations.csv"
    CHROMADB_PATH: Path = BASE_DIR / "data/chroma_db"
    CLIENT_CONFIG_PATH: Path = BASE_DIR / "data/client_configs.json"

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
