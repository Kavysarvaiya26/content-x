from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_ROOT.parent / ".env"), extra="ignore")

    app_env: str = "development"
    frontend_origin: str = "http://localhost:3000"
    database_url: str = f"sqlite:///{(BACKEND_ROOT / 'data' / 'transformai.db').as_posix()}"
    max_upload_mb: int = 10
    demo_access_token: str = ""
    llm_provider: str = "groq"
    llm_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    llm_max_concurrency: int = 1
    data_dir: Path = BACKEND_ROOT / "data"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def docs_enabled(self) -> bool:
        return self.app_env != "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings
