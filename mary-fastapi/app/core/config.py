"""Runtime settings.

Values come from the process environment. Docker Compose loads them from
.env (development) or .env.production (the droplet). Defaults are safe to
commit. Production startup rejects placeholders.
"""

from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


WEAK_SECRET_KEYS = {
    "",
    "change-me",
    "changeme",
    "secret",
    "supersecretjwtkey_change_in_production",
    "development-only-secret-key-not-for-production",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "Mary Care Management System API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DATABASE_URL: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    # Development can keep a session in this process when Redis is down.
    # Production must refuse to issue tokens in that case.
    SESSION_MEMORY_FALLBACK: bool = True
    AUTO_CREATE_TABLES: bool = True

    CORS_ORIGINS: str = (
        "http://localhost:8080,http://127.0.0.1:8080,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    PUBLIC_BASE_URL: str = "http://localhost:8080"

    SMTP_HOST: str = "send.one.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    STORAGE_PATH: str = "storage"

    def origin_list(self) -> list[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    def host_list(self) -> list[str]:
        hosts = [item.strip() for item in self.ALLOWED_HOSTS.split(",") if item.strip()]
        public = urlparse(self.PUBLIC_BASE_URL).hostname
        if public and public not in hosts:
            hosts.append(public)
        for required in ("localhost", "127.0.0.1"):
            if required not in hosts:
                hosts.append(required)
        return hosts


def validate_for_runtime(settings: Settings) -> None:
    """Stop the process when a production launch is still using dev defaults."""
    problems: list[str] = []
    environment = (settings.ENVIRONMENT or "").strip().lower()

    if not settings.DATABASE_URL:
        problems.append("DATABASE_URL is required.")
    if "my_admin_pass_01" in settings.DATABASE_URL or "change-me" in settings.DATABASE_URL:
        problems.append("DATABASE_URL still contains a placeholder password.")

    if environment == "production":
        if settings.SECRET_KEY.strip().lower() in WEAK_SECRET_KEYS or len(settings.SECRET_KEY) < 32:
            problems.append("SECRET_KEY must be a random string of at least 32 characters.")
        if settings.AUTO_CREATE_TABLES:
            problems.append("AUTO_CREATE_TABLES must be false in production. Restore a database dump instead.")
        if settings.SESSION_MEMORY_FALLBACK:
            problems.append("SESSION_MEMORY_FALLBACK must be false in production.")
        origins = settings.origin_list()
        if not origins or any(origin == "*" for origin in origins):
            problems.append("CORS_ORIGINS must list the public https origin. A wildcard is not allowed.")
        if any(not origin.startswith("https://") for origin in origins):
            problems.append("CORS_ORIGINS in production must use https origins.")
        if not settings.PUBLIC_BASE_URL.startswith("https://"):
            problems.append("PUBLIC_BASE_URL must be the public https address of the site.")
        if not urlparse(settings.REDIS_URL).password:
            problems.append("REDIS_URL must include a password in production.")
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            problems.append("SMTP_USER and SMTP_PASSWORD are required in production.")
        if not settings.host_list():
            problems.append("ALLOWED_HOSTS must include the public hostname.")
    else:
        if not settings.SECRET_KEY or settings.SECRET_KEY.strip().lower() in WEAK_SECRET_KEYS:
            problems.append("SECRET_KEY is required. Copy .env.example to .env and set one.")

    if problems:
        joined = "\n".join(f"- {item}" for item in problems)
        raise RuntimeError(f"Refusing to start.\n{joined}")


settings = Settings()
