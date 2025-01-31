"""
Configuration module for the CLI Weather Application.

Loads environment variables, defines file paths, sets default configurations,
and handles loading and saving application settings.
"""
import json
import logging
from pathlib import Path
from typing import Dict
from datetime import timedelta
from logging.handlers import RotatingFileHandler
from dotenv import dotenv_values
from .utils import CLIWeatherException

logger = logging.getLogger(__file__)

# Load environment variables
VARS = dotenv_values()
API_KEY = VARS.get("OWM_API_KEY", "")
LOCAL_TIMEZONE = VARS.get('TZ', 'UTC')
LOG_LEVEL = VARS.get("LOG_LEVEL", "ERROR")

# File paths
CONFIG_DIR = Path(__file__).resolve().parent.parent / "data"
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
CACHED_DIR = Path(__file__).resolve().parent.parent / "data/cache"

# Create paths if they dont exist.
CONFIG_DIR.mkdir(exist_ok=True, parents=True)
LOG_DIR.mkdir(exist_ok=True, parents=True)

# Configuration file for saving locations and activities.
CONFIG_FILE = CONFIG_DIR / "config.json"
# Default configuration to use if configuration file is not found or unreadable. Also used for first time users.
DEFAULT_CONFIG = {
    "locations": {"Manila": "14.5987713, 120.9833966"},
    "activities": {"walking": {
            "temp_min": 18,
            "temp_max": 30,
            "rain": 0.0,
            "wind_min": 0,
            "wind_max": 10.0,
            "time_range": [
                "00:00",
                "23:59"
            ]
        }
    }
}

# Time for cached data to expire.
CACHE_EXPIRY = timedelta(minutes=30)

# Unit for displaying activity criteria.
UNITS = {
    "temp_min": "°C",
    "temp_max": "°C",
    "rain": "mm",
    "wind_min": "km/h",
    "wind_max": "km/h",
    "time_range": ""
}


def configure_logging():
    """Configures the logging settings for the application."""
    logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers =[RotatingFileHandler(LOG_DIR / "weather_app.log", maxBytes=5 * 1024 * 1024, backupCount=3)]
)


def load_config() -> Dict:
    """Loads the configuration from the config file or returns the default."""
    if not CONFIG_FILE.exists():
        logger.warning(f"Configuration file not found. Creating default at: {CONFIG_FILE}")
        try:
            save_config(DEFAULT_CONFIG) # Create initial config file
            return DEFAULT_CONFIG
        except Exception as e:
            logger.exception(f"Error creating default config file: {e}")
            return DEFAULT_CONFIG

    try:
        with open(CONFIG_FILE, encoding='utf-8') as f:
            config = json.load(f)
            return config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        print("Error: Invalid configuration file. Using defaults.")
        return DEFAULT_CONFIG
    except Exception as e:
        logger.exception(f"An unexpected error occurred loading configuration: {e}")
        return DEFAULT_CONFIG


def save_config(data: Dict) -> None:
    """Saves the configuration data to the config file."""
    try:
        logger.debug("Saving configuration...")
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            logger.debug("Configuration saved successfully.")
    except (json.JSONDecodeError, FileNotFoundError,OSError) as e:
        logger.error(f"Error saving data to configuration: {e}")
        raise CLIWeatherException(f"Error saving data to configuration. {e}")
    except Exception as e:
        logger.exception(f"Error saving data to configuration. {e}")
