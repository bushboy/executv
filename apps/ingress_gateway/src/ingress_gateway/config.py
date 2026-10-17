from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ingress_gateway_host: str = "0.0.0.0"
    ingress_gateway_port: int = 8000
    core_engine_url: str = "http://localhost:8001"
    mcp_mount_path: str = "/mcp"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    mcp_bearer_token: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
