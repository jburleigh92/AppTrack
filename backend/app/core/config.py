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

    # File upload settings
    UPLOAD_DIR: str = "uploads"
    RESUME_UPLOAD_DIR: str = "uploads/resumes"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_RESUME_MIME_TYPES: list = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]

    HEADLESS_MIN_DESCRIPTION_LENGTH: int = 200

    # Job Matching Configuration
    # Role domain filter: configurable, not hard-coded to preserve industry-agnostic architecture
    ACTIVE_ROLE_DOMAIN: str = "technical"  # Options: "technical", "any" (future: "sales", "marketing", etc.)

    # Selective enrichment: fetch full job descriptions only for top candidates
    MAX_JOBS_TO_ENRICH: int = 75  # Fetch full descriptions for top N candidates only

    # Scoring guardrails: cap scores for title-only matches (missing job content)
    TITLE_ONLY_SCORE_CAP: int = 50  # Max score without full job description

    llm_config: Dict[str, Any] = {
        "provider": "openai",
        "model": "gpt-4",
        "temperature": 0.2,
        "max_tokens": 1500
    }

    # Role domain definitions (configuration-driven, not hard-coded)
    # Allows system to be adapted for other industries without code changes
    ROLE_DOMAINS: Dict[str, Dict[str, list]] = {
        "technical": {
            "require_any": [
                "Engineer", "Developer", "Software", "Platform", "Infrastructure",
                "DevOps", "SRE", "Architect", "Programmer", "Data Scientist",
                "Data Engineer", "ML", "AI", "Frontend", "Backend", "Fullstack",
                "Full Stack", "Full-Stack", "Mobile", "iOS", "Android", "QA",
                "Security Engineer", "Cloud Engineer"
            ],
            "exclude_any": [
                "GTM", "Go-to-Market", "Sales", "Business Development", "Partner Manager",
                "Account Manager", "Customer Success", "Marketing Manager", "Recruiting",
                "Recruiter", "HR", "Human Resources", "Finance", "Accounting",
                "Legal", "Compliance", "Operations Manager", "Product Marketing"
            ]
        },
        "any": {
            "require_any": [],
            "exclude_any": []
        }
    }

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.ENV in ["local", "dev"]:
            self.DEBUG = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()

# Create global settings instance
settings = get_settings()
