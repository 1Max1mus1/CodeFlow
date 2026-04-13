from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    moonshot_api_key: str = ""
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


SETTINGS = Settings()
