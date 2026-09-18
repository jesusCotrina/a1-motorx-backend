from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Por defecto SQLite para poder arrancar sin PostgreSQL.
    # En produccion/desarrollo real: postgresql+psycopg://taller:taller@localhost:5432/taller
    database_url: str = "sqlite+pysqlite:///./dev.db"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    refresh_token_expire_days: int = 7
    refresh_token_expire_days_recordado: int = 30

    demo_mode: bool = False

    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


settings = Settings()
