from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Dict, Any, Optional


class Settings(BaseSettings):
    ENV: str = "local"
    DEBUG: bool = True
    APP_NAME: str = "Job Application Tracker"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    
    llm_config: Dict[str, Any] = {
        "provider": "openai",
        "model": "gpt-4",
        "temperature": 0.2,
        "max_tokens": 1500
    }

    class Config:
        env_file = "backend/app/core/.env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.ENV in ["local", "dev"]:
            self.DEBUG = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
