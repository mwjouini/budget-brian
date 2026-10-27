"""Standalone configuration for cloud GitHub Actions scanner."""

from pathlib import Path
from typing import Any, Dict
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings:
    USER_AGENT = "VividJobWatcher/2.0 (+contact@example.com)"
    MIN_ALERT_SCORE = 85.0
    TIMEZONE = "Europe/London"


settings = Settings()


def load_yaml_config(file_name: str) -> Dict[str, Any]:
    file_path = CONFIG_DIR / file_name
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_keywords_config() -> Dict[str, Any]:
    return load_yaml_config("keywords.yml")
