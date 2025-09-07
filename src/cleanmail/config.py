from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Tuple, Optional, Dict, List, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, ValidationError


DEFAULT_CONFIG_PATHS = (
    Path("config.yaml"),
    Path("/app/config.yaml"),
)


def _first_existing(paths: Tuple[Path, ...]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None


class Schedule(BaseModel):
    time: str = Field(default="22:00", description="HH:MM 24h")
    timezone: str = Field(default=os.environ.get("TZ", "UTC"))

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            hh, mm = map(int, v.split(":"))
        except Exception as e:  # pragma: no cover
            raise ValueError("time must be HH:MM") from e
        if not (0 <= hh < 24 and 0 <= mm < 60):
            raise ValueError("time must have 0<=HH<24 and 0<=MM<60")
        return f"{hh:02d}:{mm:02d}"


class Mode(BaseModel):
    dry_run: bool = True
    action: Literal["keep", "archive", "trash", "label"] = "trash"
    quarantine_label: str = "ToReview"
    preserve_days: int = Field(default=7, ge=0)


class Limits(BaseModel):
    max_messages_per_run: int = Field(default=500, ge=1)
    fetch_window_hours: int = Field(default=24, ge=1)


class LLM(BaseModel):
    provider: Literal["openai"] = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_body_chars: int = Field(default=2000, ge=100)
    system_prompt_path: str = "prompts/classifier_system.md"


class Report(BaseModel):
    save_dir: str = "reports"


class Secrets(BaseModel):
    openai_api_key_env: str = "OPENAI_API_KEY"
    google_credentials_dir: str = "data/google"
    sqlite_path: str = "data/cleanmail.db"


class Safety(BaseModel):
    whitelist_senders: List[str] = Field(default_factory=list)
    whitelist_domains: List[str] = Field(default_factory=list)
    never_touch_labels: List[str] = Field(default_factory=list)


class AppConfig(BaseModel):
    schedule: Schedule = Field(default_factory=Schedule)
    mode: Mode = Field(default_factory=Mode)
    limits: Limits = Field(default_factory=Limits)
    llm: LLM = Field(default_factory=LLM)
    report: Report = Field(default_factory=Report)
    secrets: Secrets = Field(default_factory=Secrets)
    safety: Safety = Field(default_factory=Safety)


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load and validate application configuration.

    - Reads YAML from `path` or default `config.yaml` if None.
    - Applies defaults and basic validation (e.g., schedule format, enums).
    - Expands relative paths (reports dir, credentials dir, sqlite path).

    Returns a nested dict suitable for injection into components.
    """

    cfg_path: Optional[Path]
    if path:
        cfg_path = Path(path)
    else:
        cfg_path = _first_existing(DEFAULT_CONFIG_PATHS)
    if not cfg_path:
        raise FileNotFoundError("config.yaml not found; copy config.example.yaml")

    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # Defaults
    cfg.setdefault("schedule", {})
    cfg.setdefault("mode", {})
    cfg.setdefault("limits", {})
    cfg.setdefault("llm", {})
    cfg.setdefault("report", {})
    cfg.setdefault("secrets", {})
    cfg.setdefault("safety", {})

    # Expand paths
    base = cfg_path.parent
    def _expand(p: str) -> str:
        return str((base / p).resolve()) if not os.path.isabs(p) else p

    # Apply path expansion before validation so the model sees normalized paths
    if cfg.get("report", {}).get("save_dir"):
        cfg["report"]["save_dir"] = _expand(cfg["report"].get("save_dir"))
    if cfg.get("secrets", {}).get("google_credentials_dir"):
        cfg["secrets"]["google_credentials_dir"] = _expand(cfg["secrets"].get("google_credentials_dir"))
    if cfg.get("secrets", {}).get("sqlite_path"):
        cfg["secrets"]["sqlite_path"] = _expand(cfg["secrets"].get("sqlite_path"))
    if cfg.get("llm", {}).get("system_prompt_path"):
        cfg["llm"]["system_prompt_path"] = _expand(cfg["llm"].get("system_prompt_path"))

    # Validate using Pydantic, then return as plain dict
    try:
        model = AppConfig.model_validate(cfg)
    except ValidationError as e:
        # Re-raise with a concise message suitable for CLI
        raise ValueError(f"Invalid configuration: {e}")
    return model.model_dump()
