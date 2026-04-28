from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    class Config:
        env_file = ".env"

    GITHUB_CLIENT_ID: str
    BACKEND_URL: str


settings = Settings()  # type: ignore
