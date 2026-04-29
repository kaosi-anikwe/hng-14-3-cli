from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_USER_ENV = Path.home() / ".insighta" / ".env"
_LOCAL_ENV = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[str(_LOCAL_ENV), str(_USER_ENV)],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    INSIGHTA_GITHUB_CLIENT_ID: str = "Iv23lizZgswzy4egTJVu"
    INSIGHTA_BACKEND_URL: str = "https://hng-14-three.vercel.app"
    INSIGHTA_DEVELOPMENT: bool = False


settings = Settings()  # type: ignore
