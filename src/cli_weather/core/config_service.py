"""Configuration service backed by the XDG JSON store."""

from __future__ import annotations

import logging
import os
from datetime import timedelta
from pathlib import Path
from typing import Any

from ..legacy import config as storage
from .models import Activity, Location

logger = logging.getLogger(__name__)


class ConfigService:
    """Reads and writes app settings, locations, and activities."""

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = (
            Path(config_dir) if config_dir is not None else storage.get_config_dir()
        )
        self.config_file = self.config_dir / "config.json"
        self.data_dir = storage.get_data_dir()
        self.log_dir = storage.get_log_dir()
        self.cache_dir = storage.get_cache_dir()

    def load_config(self) -> dict[str, Any]:
        return storage.load_config(self.config_file)

    def save_config(self, config: dict[str, Any]) -> None:
        storage.save_config(config, self.config_file)

    @property
    def stored_api_key(self) -> str:
        return str(self.load_config().get("api_key", ""))

    @property
    def api_key(self) -> str:
        return os.getenv("OWM_API_KEY") or self.stored_api_key

    @property
    def timezone(self) -> str:
        return str(self.load_config().get("timezone") or os.getenv("TZ") or "UTC")

    @property
    def log_level(self) -> str:
        return str(
            self.load_config().get("log_level") or os.getenv("LOG_LEVEL") or "ERROR"
        )

    @property
    def cache_expiry(self) -> timedelta:
        return storage.CACHE_EXPIRY

    def setup_logging(self) -> None:
        storage.configure_logging(self.log_dir, self.log_level)

    def get_locations(self) -> dict[str, Location]:
        locations = {}
        for name, coords in self.load_config().get("locations", {}).items():
            try:
                locations[name] = Location.from_coordinates(name, coords)
            except ValueError as exc:
                logger.warning("Invalid location %s: %s", name, exc)
        return locations

    def save_location(self, location: Location) -> None:
        config = self.load_config()
        config.setdefault("locations", {})[location.name] = location.to_coord_string()
        self.save_config(config)

    def delete_location(self, location_name: str) -> bool:
        config = self.load_config()
        if location_name not in config.get("locations", {}):
            return False
        del config["locations"][location_name]
        self.save_config(config)
        return True

    def get_activities(self) -> dict[str, Activity]:
        activities = {}
        for name, data in self.load_config().get("activities", {}).items():
            try:
                activities[name] = Activity.from_dict(name, data)
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Invalid activity %s: %s", name, exc)
        return activities

    def save_activity(self, activity: Activity) -> None:
        config = self.load_config()
        config.setdefault("activities", {})[activity.name] = activity.to_dict()
        self.save_config(config)

    def delete_activity(self, activity_name: str) -> bool:
        config = self.load_config()
        if activity_name not in config.get("activities", {}):
            return False
        del config["activities"][activity_name]
        self.save_config(config)
        return True
