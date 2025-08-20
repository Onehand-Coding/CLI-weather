"""Configuration service for managing app settings and data persistence."""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import timedelta
from logging.handlers import RotatingFileHandler

from dotenv import dotenv_values

from .exceptions import ConfigError
from .models import Location, Activity

logger = logging.getLogger(__name__)


class ConfigService:
    """Handles configuration management and persistence."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration service.
        
        Args:
            config_dir: Optional custom config directory
        """
        if config_dir is None:
            # Find project root
            current_dir = Path(__file__).parent.parent
            while not (current_dir / "pyproject.toml").exists():
                if current_dir == current_dir.parent:
                    raise ConfigError("Could not find project root containing 'pyproject.toml'")
                current_dir = current_dir.parent
            self.root_dir = current_dir
        else:
            self.root_dir = config_dir.parent if config_dir.name != "data" else config_dir.parent
            
        # Set up directories
        self.config_dir = self.root_dir / "data"
        self.log_dir = self.root_dir / "logs"
        self.cache_dir = self.root_dir / "data/cache"
        
        # Create directories if they don't exist
        self.config_dir.mkdir(exist_ok=True, parents=True)
        self.log_dir.mkdir(exist_ok=True, parents=True)
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        
        # Configuration file
        self.config_file = self.config_dir / "config.json"
        
        # Load environment variables
        self._env_vars = dotenv_values()
        
        # Default configuration
        self._default_config = {
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
    
    @property
    def api_key(self) -> str:
        """Get OpenWeatherMap API key from environment."""
        return self._env_vars.get("OWM_API_KEY", "")
    
    @property
    def timezone(self) -> str:
        """Get timezone from environment."""
        return self._env_vars.get("TZ", "UTC")
    
    @property
    def log_level(self) -> str:
        """Get log level from environment."""
        return self._env_vars.get("LOG_LEVEL", "ERROR")
    
    @property
    def cache_expiry(self) -> timedelta:
        """Get cache expiry duration."""
        return timedelta(minutes=30)
    
    def setup_logging(self) -> None:
        """Configure application logging."""
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                RotatingFileHandler(
                    self.log_dir / "weather_app.log", 
                    maxBytes=5 * 1024 * 1024, 
                    backupCount=3
                )
            ],
        )
    
    def load_config(self) -> Dict:
        """Load configuration from file or return default."""
        if not self.config_file.exists():
            logger.warning(f"Configuration file not found. Creating default at: {self.config_file}")
            try:
                self.save_config(self._default_config)
                return self._default_config.copy()
            except Exception as e:
                logger.exception(f"Error creating default config file: {e}")
                return self._default_config.copy()
        
        try:
            with open(self.config_file, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise ConfigError("Invalid configuration file format") from e
        except Exception as e:
            logger.exception(f"Error loading configuration: {e}")
            raise ConfigError(f"Failed to load configuration: {e}") from e
    
    def save_config(self, config: Dict) -> None:
        """Save configuration to file."""
        try:
            logger.debug("Saving configuration...")
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            logger.debug("Configuration saved successfully.")
        except Exception as e:
            logger.exception(f"Error saving configuration: {e}")
            raise ConfigError(f"Failed to save configuration: {e}") from e
    
    def get_locations(self) -> Dict[str, Location]:
        """Get all saved locations as Location objects."""
        config = self.load_config()
        locations = {}
        
        # Load from config file
        for name, coords in config.get("locations", {}).items():
            try:
                locations[name] = Location.from_coordinates(name, coords)
            except ValueError as e:
                logger.warning(f"Invalid location coordinates for {name}: {e}")
        
        # Load sensitive locations from environment
        for key, value in self._env_vars.items():
            try:
                if self._is_valid_coordinates(value):
                    locations[key] = Location.from_coordinates(key, value)
            except (ValueError, TypeError):
                continue
                
        return locations
    
    def save_location(self, location: Location) -> None:
        """Save a location to configuration."""
        config = self.load_config()
        config.setdefault("locations", {})[location.name] = f"{location.latitude}, {location.longitude}"
        self.save_config(config)
        logger.debug(f"Location '{location.name}' saved successfully.")
    
    def delete_location(self, location_name: str) -> bool:
        """Delete a location from configuration."""
        config = self.load_config()
        if location_name in config.get("locations", {}):
            del config["locations"][location_name]
            self.save_config(config)
            logger.debug(f"Location '{location_name}' deleted successfully.")
            return True
        return False
    
    def get_activities(self) -> Dict[str, Activity]:
        """Get all saved activities as Activity objects."""
        config = self.load_config()
        activities = {}
        
        for name, data in config.get("activities", {}).items():
            try:
                activities[name] = Activity.from_dict(name, data)
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid activity data for {name}: {e}")
        
        return activities
    
    def save_activity(self, activity: Activity) -> None:
        """Save an activity to configuration."""
        config = self.load_config()
        config.setdefault("activities", {})[activity.name] = activity.to_dict()
        self.save_config(config)
        logger.debug(f"Activity '{activity.name}' saved successfully.")
    
    def delete_activity(self, activity_name: str) -> bool:
        """Delete an activity from configuration."""
        config = self.load_config()
        if activity_name in config.get("activities", {}):
            del config["activities"][activity_name]
            self.save_config(config)
            logger.debug(f"Activity '{activity_name}' deleted successfully.")
            return True
        return False
    
    def _is_valid_coordinates(self, value: str) -> bool:
        """Check if a string represents valid latitude/longitude coordinates."""
        try:
            lat, lon = map(float, value.split(","))
            return -90 <= lat <= 90 and -180 <= lon <= 180
        except (ValueError, TypeError, AttributeError):
            return False
