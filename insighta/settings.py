from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    GITHUB_CLIENT_ID: str = "Iv23lizZgswzy4egTJVu"
    BACKEND_URL: str = "https://hng-14-three.vercel.app"
    DEVELOPMENT: bool = False


settings = Settings()  # type: ignore
