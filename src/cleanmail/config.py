from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Tuple, Optional, Dict

import yaml


DEFAULT_CONFIG_PATHS = (
    Path("config.yaml"),
    Path("/app/config.yaml"),
)


def _first_existing(paths: Tuple[Path, ...]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None


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
    cfg.setdefault("schedule", {}).setdefault("time", "22:00")
    cfg["schedule"].setdefault("timezone", os.environ.get("TZ", "UTC"))
    cfg.setdefault("mode", {}).setdefault("dry_run", True)
    cfg["mode"].setdefault("action", "trash")
    cfg["mode"].setdefault("quarantine_label", "ToReview")
    cfg["mode"].setdefault("preserve_days", 7)
    cfg.setdefault("limits", {}).setdefault("max_messages_per_run", 500)
    cfg["limits"].setdefault("fetch_window_hours", 24)
    cfg.setdefault("llm", {}).setdefault("provider", "openai")
    cfg["llm"].setdefault("model", "gpt-4o-mini")
    cfg["llm"].setdefault("temperature", 0.0)
    cfg["llm"].setdefault("max_body_chars", 2000)
    cfg["llm"].setdefault("system_prompt_path", "prompts/classifier_system.md")
    cfg.setdefault("report", {}).setdefault("save_dir", "reports")
    cfg.setdefault("secrets", {}).setdefault("openai_api_key_env", "OPENAI_API_KEY")
    cfg["secrets"].setdefault("google_credentials_dir", "data/google")
    cfg["secrets"].setdefault("sqlite_path", "data/cleanmail.db")

    # Expand paths
    base = cfg_path.parent
    def _expand(p: str) -> str:
        return str((base / p).resolve()) if not os.path.isabs(p) else p

    cfg["report"]["save_dir"] = _expand(cfg["report"]["save_dir"])
    cfg["secrets"]["google_credentials_dir"] = _expand(cfg["secrets"]["google_credentials_dir"])
    cfg["secrets"]["sqlite_path"] = _expand(cfg["secrets"]["sqlite_path"])
    cfg["llm"]["system_prompt_path"] = _expand(cfg["llm"]["system_prompt_path"])

    return cfg
