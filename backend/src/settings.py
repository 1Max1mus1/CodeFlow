from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    xiaomi_token_plan_cn_api_key: str = ""
    anthropic_auth_token: str = ""
    mimo_token_plan_cn_base_url: str = "https://token-plan-cn.xiaomimimo.com/anthropic"
    mimo_model: str = "mimo-v2.5-pro"
    mimo_api_timeout_seconds: float = 120.0
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def mimo_token_plan_cn_api_key(self) -> str:
        return self.xiaomi_token_plan_cn_api_key or self.anthropic_auth_token

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


SETTINGS = Settings()
