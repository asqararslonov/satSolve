import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
OUTPUT_DIR = BASE_DIR / "data" / "outputs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load existing .env if present
load_dotenv(BASE_DIR / ".env")


class AppConfig(BaseModel):
    ai_provider: str = Field(
        default_factory=lambda: os.getenv("AI_PROVIDER", "openrouter").lower()
    )
    openrouter_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY", "")
    )
    anthropic_api_key: str = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )
    vision_model: str = Field(
        default_factory=lambda: os.getenv(
            "VISION_MODEL", "anthropic/claude-3.7-sonnet"
        )
    )
    solver_model: str = Field(
        default_factory=lambda: os.getenv(
            "SOLVER_MODEL", "anthropic/claude-3-opus"
        )
    )
    max_concurrency: int = Field(
        default_factory=lambda: int(os.getenv("MAX_CONCURRENCY", "4"))
    )
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    host: str = Field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))

    def get_api_key(self, provider: str | None = None) -> str:
        prov = (provider or self.ai_provider).lower()
        if prov == "anthropic":
            return self.anthropic_api_key
        return self.openrouter_api_key

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)


# Global config instance
config = AppConfig()
