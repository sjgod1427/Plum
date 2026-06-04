from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = ""  # Must be verified in SendGrid Sender Authentication
    DATABASE_URL: str = "sqlite:///./claims.db"
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    POLICY_TERMS_PATH: str = "./policy_terms.json"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
