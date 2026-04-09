from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Estate Workforce Intelligence"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./estate_workforce.db"
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173"
    DEFAULT_JOB_CODE_SEED: str = str(Path(__file__).resolve().parents[2] / "data" / "job_codes_seed.csv")
    USER_ACCESS_FILE: str = str(Path(__file__).resolve().parents[2] / "data" / "user_estate_access.json")
    USER_CREDENTIALS_FILE: str = str(Path(__file__).resolve().parents[2] / "data" / "estate_credentials_reference.json")
    ACCESS_STRICT_MODE: bool = True

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
