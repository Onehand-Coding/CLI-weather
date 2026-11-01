"""XDG-backed configuration storage for CLI Weather.

The application stores its API key, preferences, locations, and activities in a
single JSON file. No .env file is read.
"""

from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from datetime import timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .utils import CLIWeatherException

logger = logging.getLogger(__name__)


def _xdg_path(env_name: str, default: Path) -> Path:
    return Path(os.getenv(env_name, default)).expanduser()


def _home() -> Path:
    return Path.home()


def get_config_dir() -> Path:
    override = os.getenv("CLI_WEATHER_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    return _xdg_path("XDG_CONFIG_HOME", _home() / ".config") / "cli-weather"


def get_data_dir() -> Path:
    override = os.getenv("CLI_WEATHER_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return _xdg_path("XDG_DATA_HOME", _home() / ".local" / "share") / "cli-weather"


def get_cache_dir() -> Path:
    override = os.getenv("CLI_WEATHER_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    return _xdg_path("XDG_CACHE_HOME", _home() / ".cache") / "cli-weather"


def get_log_dir() -> Path:
    override = os.getenv("CLI_WEATHER_LOG_DIR")
    if override:
        return Path(override).expanduser()
    return (
        _xdg_path("XDG_STATE_HOME", _home() / ".local" / "state")
        / "cli-weather"
        / "logs"
    )


CONFIG_DIR = get_config_dir()
DATA_DIR = get_data_dir()
CACHE_DIR = get_cache_dir()
LOG_DIR = get_log_dir()
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "api_key": "",
    "timezone": "UTC",
    "log_level": "ERROR",
    "locations": {"Manila": "14.5987713, 120.9833966"},
    "activities": {
        "walking": {
            "temp_min": 18,
            "temp_max": 30,
            "rain": 0.0,
            "wind_min": 0,
            "wind_max": 10.0,
            "time_range": ["00:00", "23:59"],
        }
    },
}

CACHE_EXPIRY = timedelta(minutes=30)
VARS: dict[str, str] = {}
UNITS = {
    "temp_min": "°C",
    "temp_max": "°C",
    "rain": "mm",
    "wind_min": "km/h",
    "wind_max": "km/h",
    "time_range": "",
}


def _default_config() -> dict[str, Any]:
    return deepcopy(DEFAULT_CONFIG)


def _resolve_config_file(config_file: Path | None) -> Path:
    return Path(config_file) if config_file is not None else CONFIG_FILE


def load_config(config_file: Path | None = None) -> dict[str, Any]:
    """Load the config, returning defaults when it is missing or invalid."""
    path = _resolve_config_file(config_file)
    if not path.exists():
        return _default_config()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        logger.error("Could not read configuration at %s: %s", path, exc)
        return _default_config()

    if not isinstance(raw, dict):
        logger.error("Configuration at %s is not a JSON object.", path)
        return _default_config()

    config = _default_config()
    config.update(raw)
    return config


def save_config(data: dict[str, Any], config_file: Path | None = None) -> None:
    """Write the config with restrictive permissions where supported."""
    path = _resolve_config_file(config_file)
    payload = _default_config()
    payload.update(data)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            os.chmod(path.parent, 0o700)
        path.write_text(json.dumps(payload, indent=4) + "\n", encoding="utf-8")
        if os.name == "posix":
            os.chmod(path, 0o600)
    except OSError as exc:
        raise CLIWeatherException(f"Failed to save configuration: {exc}") from exc


def get_api_key() -> str:
    return os.getenv("OWM_API_KEY") or str(load_config().get("api_key", ""))


def get_timezone() -> str:
    return str(load_config().get("timezone") or os.getenv("TZ") or "UTC")


def get_log_level() -> str:
    return str(load_config().get("log_level") or os.getenv("LOG_LEVEL") or "ERROR")


API_KEY = get_api_key()
LOCAL_TIMEZONE = get_timezone()
LOG_LEVEL = get_log_level()


def configure_logging(log_dir: Path | None = None) -> None:
    """Configure file logging under the XDG state directory."""
    directory = Path(log_dir) if log_dir is not None else LOG_DIR
    directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, get_log_level().upper(), logging.ERROR),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(
                directory / "weather_app.log",
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
            )
        ],
        force=True,
    )
