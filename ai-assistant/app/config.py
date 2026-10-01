from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_db: str = "ai_assistant"
    postgres_user: str = "ai_assistant"
    postgres_password: str = "ai_assistant"
    postgres_host: str = "db"
    postgres_port: str = "5432"

    service_token: str = "change-me"

    ai_base_url: str = "https://ai.tanakatatsuki.dev/v1"
    ai_api_key: str = ""
    default_chat_model: str = "gemini-3.8-flash-low"
    default_image_model: str = "gemini-3.1-flash-image"
    high_quality_image_model: str = "gemini-3-pro-image"

    chroma_path: str = "/app/chroma_data"
    media_root: str = "/app/media"
    embedding_model: str = "intfloat/multilingual-e5-small"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
