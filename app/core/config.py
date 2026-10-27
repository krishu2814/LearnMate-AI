from typing import Optional
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # General App Settings
    PROJECT_NAME: str = "LearnMate AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security & Tokens
    SECRET_KEY: str = "insecure_dev_secret_key_change_in_production_32bytes_minimum"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # MySQL Database Settings
    MYSQL_SERVER: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "learnmate_user"
    MYSQL_PASSWORD: str = "learnmate_password"
    MYSQL_DB: str = "learnmate_db"

    # Redis Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # AI Provider Settings
    GEMINI_API_KEY: Optional[str] = None

    @computed_field
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_SERVER}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"
        )

    @computed_field
    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_SERVER}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"
        )

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"


settings = Settings()
