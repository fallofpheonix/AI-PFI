from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    LOG_LEVEL: str = "INFO"
    OUTPUT_DIR: str = "./out"
    REQUEST_TIMEOUT: int = 30
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    # Storage
    CHROMA_DB_PATH: str = "./chroma_db"
    
    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8001
    
    # For sentence-transformers/huggingface
    HF_HOME: Optional[str] = None

settings = Settings()
