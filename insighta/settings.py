from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GITHUB_CLIENT_ID: str

    class Config:
        env_file = ".env"

settings = Settings() # type: ignore