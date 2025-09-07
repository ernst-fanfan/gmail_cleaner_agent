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
        # Validate format strictly without broad exception catches
        if not isinstance(v, str):
            raise ValueError("time must be HH:MM")
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("time must be HH:MM")
        try:
            hh = int(parts[0])
            mm = int(parts[1])
        except ValueError as e:
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

    # Helper to DRY path expansion
    def _expand_field(section: str, key: str) -> None:
        sect = cfg.get(section)
        if not isinstance(sect, dict):
            return
        val = sect.get(key)
        if isinstance(val, str) and val:
            sect[key] = _expand(val)

    # Apply path expansion before validation so the model sees normalized paths
    for section, key in (
        ("report", "save_dir"),
        ("secrets", "google_credentials_dir"),
        ("secrets", "sqlite_path"),
        ("llm", "system_prompt_path"),
    ):
        _expand_field(section, key)

    # Validate using Pydantic, then return as plain dict
    try:
        model = AppConfig.model_validate(cfg)
    except ValidationError as e:
        # Preserve detailed field validation errors for clearer CLI output
        details = []
        for err in e.errors():
            loc = ".".join(str(p) for p in err.get("loc", []))
            msg = err.get("msg", "validation error")
            typ = err.get("type", "")
            details.append(f"- {loc}: {msg}{f' ({typ})' if typ else ''}")
        raise ValueError("Invalid configuration:\n" + "\n".join(details))
    return model.model_dump()
