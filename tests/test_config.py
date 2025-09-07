import os
from pathlib import Path

import pytest

from src.cleanmail.config import load_config


def write_cfg(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_config_defaults(tmp_path):
    # Empty config should be filled with sane defaults
    cfg_file = write_cfg(tmp_path, "---\n")
    cfg = load_config(str(cfg_file))

    assert cfg["schedule"]["time"] == "22:00"
    assert "timezone" in cfg["schedule"]
    assert cfg["mode"]["dry_run"] is True
    assert cfg["mode"]["action"] in {"keep", "archive", "trash", "label"}
    assert isinstance(cfg["limits"]["max_messages_per_run"], int)
    assert isinstance(cfg["limits"]["fetch_window_hours"], int)


def test_invalid_time_raises(tmp_path):
    bad = (
        "schedule:\n"
        "  time: '25:00'\n"
    )
    cfg_file = write_cfg(tmp_path, bad)
    with pytest.raises(ValueError):
       load_config(str(cfg_file))


def test_path_expansion(tmp_path):
    cfg_text = (
        "report:\n"
        "  save_dir: 'reports'\n"
        "secrets:\n"
        "  google_credentials_dir: 'data/google'\n"
        "  sqlite_path: 'data/cleanmail.db'\n"
        "llm:\n"
        "  system_prompt_path: 'prompts/classifier_system.md'\n"
    )
    cfg_file = write_cfg(tmp_path, cfg_text)
    cfg = load_config(str(cfg_file))

    # Provided relative paths are expanded to absolute paths based on the config directory
    assert Path(cfg["report"]["save_dir"]).is_absolute()
    assert Path(cfg["secrets"]["google_credentials_dir"]).is_absolute()
    assert Path(cfg["secrets"]["sqlite_path"]).is_absolute()
    assert Path(cfg["llm"]["system_prompt_path"]).is_absolute()

