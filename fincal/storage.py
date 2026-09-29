"""File locations and settings.yaml persistence."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from fincal.models import Settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"
SETTINGS_FILE = "settings.yaml"
LOG_FILE = "spending_log.xlsx"


class SettingsError(ValueError):
    pass


def data_dir() -> Path:
    """FINCAL_DATA_DIR, else ./data; falls back to examples/ when it has no settings."""
    configured = Path(os.environ.get("FINCAL_DATA_DIR", PROJECT_ROOT / "data"))
    if (configured / SETTINGS_FILE).exists():
        return configured
    return EXAMPLES_DIR


def is_example_data(directory: Path | None = None) -> bool:
    return (directory or data_dir()).resolve() == EXAMPLES_DIR.resolve()


def settings_path(directory: Path | None = None) -> Path:
    return (directory or data_dir()) / SETTINGS_FILE


def log_path(directory: Path | None = None) -> Path:
    return (directory or data_dir()) / LOG_FILE


def load_settings(path: Path | None = None) -> Settings:
    path = path or settings_path()
    if not path.exists():
        return Settings()
    with path.open(encoding="utf-8") as f:
        return Settings.from_dict(yaml.safe_load(f))


def save_settings(settings: Settings, path: Path | None = None) -> None:
    errors = settings.validate()
    if errors:
        raise SettingsError("; ".join(errors))
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(settings.to_dict(), f, sort_keys=False, allow_unicode=True)
    tmp.replace(path)
