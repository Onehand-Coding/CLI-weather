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
    """Setup logging for ease of debugging."""
    logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers =[RotatingFileHandler(LOG_DIR / "app.log", maxBytes=5 * 1024 * 1024, backupCount=3)]
)


def load_config() -> Dict:
    """Load the configuration file to get data."""
    try:
        logging.debug("Loading configuration...")
        with open(CONFIG_FILE, encoding='utf-8') as f:
            config = json.load(f)
            logging.debug("Configuration loaded successfully.")
            return config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Failed to load configuration file: {e}")
        raise CLIWeatherException("Failed to load configuration file.")


def save_config(data: Dict) -> None:
    """Write data to configuration file."""
    try:
        logging.debug("Saving configuration...")
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            logging.debug("Configuration saved successfully.")
    except (json.JSONDecodeError, FileNotFoundError,OSError) as e:
        logging.error(f"Error saving data to configuration: {e}")
        raise CLIWeatherException("Error saving data to configuration.")
    except Exception:
        raise
