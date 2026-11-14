"""Settings, from environment variables (and app/backend/.env in local dev).

Every mock-to-real swap is one setting:
    ARTIFACTS_DIR  app/contract/mocks  ->  shared/artifacts      (rules, thresholds, model)
    AGENT          mock                ->  claude                (research agent; needs ANTHROPIC_API_KEY)
    ANSWERER       mock                ->  jev                   (needs TYPESAFE_API_KEY)
    DECIDER        mock                ->  kev                   (endpoint from model.json; KEV_API_KEY if needed)
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .contract import REPO_ROOT

BACKEND_DIR = REPO_ROOT / "app" / "backend"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore",
                                      env_ignore_empty=True)

    env: Literal["dev", "prod"] = "dev"

    # Mock-to-real switches
    artifacts_dir: str = "app/contract/mocks"
    agent: Literal["mock", "claude"] = "mock"
    answerer: Literal["mock", "jev"] = "mock"
    decider: Literal["mock", "kev"] = "mock"

    # Keys (never committed; set them in the host's dashboard)
    anthropic_api_key: SecretStr | None = None
    typesafe_api_key: SecretStr | None = None
    kev_api_key: SecretStr | None = None
    elevenlabs_api_key: SecretStr | None = None
    vapid_public_key: str | None = None
    vapid_private_key: SecretStr | None = None
    vapid_subject: str | None = None  # e.g. mailto:you@example.com, required by web push

    # Research agent (task 3)
    agent_model: str = "claude-opus-5-5"
    agent_max_searches: int = 15

    # Service behaviour
    contract_dir: str = "app/contract"
    cors_origins: str = "http://localhost:3000"
    cors_origin_regex: str | None = None  # e.g. https://.*\.vercel\.app for preview deploys
    access_token: SecretStr | None = None  # if set, /v1/* needs X-Access-Token (or ?access_token=)
    retention_minutes: int = 120  # jobs, memos and batches are kept in memory only, this long
    max_concurrent_screenings: int = 4
    batch_max_concurrency: int = 3
    mock_pace: float = 1.0  # scales the mock agent's simulated delays (0 = instant)
    validate_responses: bool = True  # check every response against the contract

    def path(self, value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else REPO_ROOT / p

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def key_status(self) -> dict[str, bool]:
        """Which keys are set (never their values)."""
        names = ("anthropic_api_key", "typesafe_api_key", "kev_api_key", "elevenlabs_api_key", "vapid_private_key")
        return {n.upper(): getattr(self, n) is not None and bool(getattr(self, n).get_secret_value()) for n in names}


def secret(value: SecretStr | None) -> str | None:
    return value.get_secret_value() if value is not None else None
