"""Settings, from environment variables (and app/backend/.env in local dev).

Every mock-to-real swap is one setting:
    ARTIFACTS_DIR  app/contract/mocks  ->  shared/artifacts      (rules, thresholds, model)
    AGENT          mock                ->  claude                (research agent; needs ANTHROPIC_API_KEY)
    ANSWERER       mock                ->  jev                   (needs TYPESAFE_API_KEY)
    DECIDER        mock                ->  kev                   (endpoint from model.json; KEV_API_KEY if needed)
    TRANSCRIBER    auto: mock          ->  elevenlabs            (voice notes; needs ELEVENLABS_API_KEY)
    NOTE_SORTER    auto: off           ->  claude                (notes -> form fields; needs ANTHROPIC_API_KEY)
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .contract import REPO_ROOT

BACKEND_DIR = REPO_ROOT / "app" / "backend"

# Local dev: also put app/backend/.env into the process environment, where SDKs that read their own key look
# (ELEVENLABS_API_KEY; the ElevenLabs onboarding sets it up this way). It never overrides a real environment
# variable, and a host such as Railway has no .env file, so there it does nothing.
load_dotenv(BACKEND_DIR / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore",
                                      env_ignore_empty=True, populate_by_name=True)

    env: Literal["dev", "prod"] = "dev"

    # Mock-to-real switches
    artifacts_dir: str = "app/contract/mocks"
    agent: Literal["mock", "claude"] = "mock"
    answerer: Literal["mock", "jev"] = "mock"
    decider: Literal["mock", "kev"] = "mock"

    # Keys (never committed; set them in the host's dashboard)
    # In this cloud sandbox use SCREENER_ANTHROPIC_API_KEY: Claude Code itself reads ANTHROPIC_API_KEY.
    anthropic_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("SCREENER_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"))
    typesafe_api_key: SecretStr | None = None
    kev_api_key: SecretStr | None = None
    elevenlabs_api_key: SecretStr | None = None
    vapid_public_key: str | None = None
    vapid_private_key: SecretStr | None = None
    vapid_subject: str | None = None  # e.g. mailto:you@example.com, required by web push

    # Research agent (AGENT=claude)
    agent_model: str = "claude-opus-5-5"
    agent_base_url: str = "https://api.anthropic.com"  # explicit: ignores any ANTHROPIC_BASE_URL in the env
    agent_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    agent_max_tokens: int = 16000
    agent_max_searches: int = 10
    agent_max_fetches: int = 5
    agent_min_confidence: float = 0.5
    agent_max_cost_per_founder_usd: float = 1.0
    agent_budget_usd: float = 5.0  # total research spend for this process; then research stops

    # Voice notes (MASTER_PLAN 8b): speech-to-text, then sorting notes into form fields the investor checks.
    # "auto" picks the real service when its key is set: ElevenLabs for speech, Claude for sorting.
    transcriber: Literal["auto", "mock", "elevenlabs"] = "auto"  # auto without ELEVENLABS_API_KEY: mock
    transcriber_model: str = "scribe_v3"
    note_max_audio_mb: float = 8.0
    note_sorter: Literal["auto", "mock", "claude", "off"] = "auto"  # auto without the Claude key: off
    note_sorter_model: str = "claude-opus-5-5"
    note_sorter_effort: Literal["low", "medium", "high", "xhigh", "max"] = "low"

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
        names = {"ANTHROPIC_API_KEY": "anthropic_api_key", "TYPESAFE_API_KEY": "typesafe_api_key",
                 "KEV_API_KEY": "kev_api_key", "ELEVENLABS_API_KEY": "elevenlabs_api_key",
                 "VAPID_PRIVATE_KEY": "vapid_private_key"}
        return {label: getattr(self, n) is not None and bool(getattr(self, n).get_secret_value()) for label, n in names.items()}


def secret(value: SecretStr | None) -> str | None:
    return value.get_secret_value() if value is not None else None
