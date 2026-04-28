from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    class Config:
        env_file = ".env"

    GITHUB_CLIENT_ID: str
    BACKENC_URL: str


settings = Settings()  # type: ignore
