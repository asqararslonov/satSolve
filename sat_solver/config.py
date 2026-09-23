import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent

if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    UPLOAD_DIR = Path("/tmp/data/uploads")
    OUTPUT_DIR = Path("/tmp/data/outputs")
else:
    UPLOAD_DIR = BASE_DIR / "data" / "uploads"
    OUTPUT_DIR = BASE_DIR / "data" / "outputs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load existing .env if present
load_dotenv(BASE_DIR / ".env")


class AppConfig(BaseModel):
    ai_provider: str = Field(
        default_factory=lambda: os.getenv("AI_PROVIDER", "omniroute").lower()
    )
    omni_route_url: str = Field(
        default_factory=lambda: os.getenv(
            "OMNI_ROUTE_URL",
            "https://34.59.24.49.nip.io:20130/v1/chat/completions",
        )
    )
    omni_route_api_key: str = Field(
        default_factory=lambda: os.getenv(
            "OMNI_ROUTE_API_KEY",
            "sk-e1c9718b5e58a095-53cb5c-fab29a1c",
        )
    )
    openrouter_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY", "")
    )
    anthropic_api_key: str = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )
    vision_model: str = Field(
        default_factory=lambda: os.getenv(
            "VISION_MODEL", "antigravity/claude-sonnet-4-6"
        )
    )
    solver_model: str = Field(
        default_factory=lambda: os.getenv(
            "SOLVER_MODEL", "antigravity/claude-opus-4-6-thinking"
        )
    )
    max_concurrency: int = Field(
        default_factory=lambda: int(os.getenv("MAX_CONCURRENCY", "4"))
    )
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    host: str = Field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))

    def get_api_key(self, provider: str | None = None) -> str:
        prov = (provider or self.ai_provider).lower()
        if prov == "omniroute":
            return self.omni_route_api_key
        elif prov == "anthropic":
            return self.anthropic_api_key
        return self.openrouter_api_key

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)


# Global config instance
config = AppConfig()
