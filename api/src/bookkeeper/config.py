from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILES: tuple[str, ...] = ("../.env", "../.env.local", ".env", ".env.local")

_SETTINGS_CONFIG = SettingsConfigDict(
    env_file=ENV_FILES,
    env_file_encoding="utf-8",
    env_ignore_empty=True,
    case_sensitive=False,
    extra="ignore",
)


class ConfigError(RuntimeError):
    pass


class Settings(BaseSettings):
    """See planning/03-tech-stack.md#11-environment-variables-names-only."""

    model_config = _SETTINGS_CONFIG

    app_env: Literal["dev", "test", "production"] = "dev"
    tz_default: str = "Asia/Singapore"
    log_level: str = "info"

    database_url: str
    storage_dir: Path = Path("./storage")

    public_base_url: str
    web_app_url: str = "http://localhost:5173"

    telegram_bot_token: str
    telegram_bot_username: str
    telegram_webhook_secret: str

    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    boss_email: str

    session_secret: str
    session_max_age_days: int = 14

    # See planning/decisions.md#D-016
    gemini_api_key: str
    gemini_model_extract: str = "gemini-3.5-flash-lite"
    gemini_model_extract_escalate: str = ""
    gemini_model_revise: str = "gemini-3.5-flash-lite"
    gemini_model_excel_map: str = "gemini-3.5-flash-lite"
    gemini_model_assistant: str = "gemini-3.5-flash-lite"
    gemini_model_sales: str = "gemini-3.5-flash-lite"
    gemini_model_router: str = "gemini-3.5-flash-lite"
    gemini_model_reply: str = "gemini-3.5-flash-lite"
    gemini_model_embed: str = "gemini-embedding-2"
    llm_timeout_seconds: int = 60

    e2e_test_login: bool = False

    @model_validator(mode="after")
    def _check_test_login(self) -> Self:
        # See planning/03-tech-stack.md#12-testing-strategy
        if self.e2e_test_login and self.app_env != "test":
            raise ValueError("E2E_TEST_LOGIN is set but APP_ENV is not 'test'")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


class DatabaseSettings(BaseSettings):
    model_config = _SETTINGS_CONFIG

    database_url: str


REQUIRED_ENV_VARS: tuple[str, ...] = tuple(
    name.upper() for name, field in Settings.model_fields.items() if field.is_required()
)

ALL_ENV_VARS: frozenset[str] = frozenset(
    {name.upper() for name in Settings.model_fields}
    | {
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "DOMAIN",
        "TEST_DATABASE_URL",
        "NGROK_AUTHTOKEN",
    }
)


def _format_error(exc: ValidationError) -> str:
    missing: list[str] = []
    invalid: list[str] = []
    for err in exc.errors():
        name = ".".join(str(part) for part in err["loc"]).upper()
        if err["type"] == "missing":
            missing.append(name)
        elif name:
            invalid.append(f"{name}: {err['msg']}")
        else:
            invalid.append(str(err["msg"]))
    lines: list[str] = []
    if missing:
        lines.append("Missing required environment variables: " + ", ".join(missing))
    if invalid:
        lines.append("Invalid environment variables: " + "; ".join(invalid))
    lines.append("See .env.example and planning/03-tech-stack.md section 11.")
    return "\n".join(lines)


def load_settings(**overrides: Any) -> Settings:
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        raise ConfigError(_format_error(exc)) from exc


def load_database_settings(**overrides: Any) -> DatabaseSettings:
    try:
        return DatabaseSettings(**overrides)
    except ValidationError as exc:
        raise ConfigError(_format_error(exc)) from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
