from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Database and seed settings loaded from the environment / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    postgres_user: str = "executv"
    postgres_password: str = "executv"
    postgres_db: str = "executv"

    database_url: str | None = None
    async_database_url: str | None = None
    sql_echo: bool = False

    seed_executive_name: str = "Avery Chen"
    seed_executive_title: str = "Chief Executive Officer"
    seed_fire_tv_device_name: str = "Boardroom Fire TV"

    @property
    def sync_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_url(self) -> str:
        if self.async_database_url:
            return self.async_database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
