"""
Core location service module.

This module contains the business logic for location operations,
separated from any UI concerns.
"""

import logging
from typing import Dict, Tuple, Optional, List
from json.decoder import JSONDecodeError

import geopy
import requests
from geopy.geocoders import Nominatim
from geopy.exc import (
    GeocoderTimedOut,
    GeocoderServiceError,
    GeocoderUnavailable,
    GeocoderParseError,
)

from ..legacy.config import VARS, load_config, save_config
from ..legacy.utils import CLIWeatherException

logger = logging.getLogger(__name__)


class Location:
    """Data class for location information."""
    
    def __init__(self, name: str, latitude: float, longitude: float, address: Optional[str] = None):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.address = address or name
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "address": self.address
        }
    
    def to_coord_string(self) -> str:
        """Convert to coordinate string format for compatibility."""
        return f"{self.latitude}, {self.longitude}"


class LocationService:
    """Core location service for managing locations and geocoding."""
    
    def __init__(self):
        self.geolocator = Nominatim(user_agent="weather_assistant", timeout=10)
        geopy.adapters.BaseAdapter.session = requests.Session()
    
    def is_valid_coordinate(self, value: str) -> bool:
        """Checks if a given string represents valid latitude/longitude coordinates."""
        try:
            logger.debug(f"Checking if '{value}' is valid location coordinate.")
            lat, lon = map(float, value.split(","))
            return -90 <= lat <= 90 and -180 <= lon <= 180
        except (ValueError, TypeError):
            return False
    
    def load_locations(self, include_sensitive: bool = False) -> Dict[str, Location]:
        """Loads location data from config and optionally from environment variables."""
        logger.debug("Loading locations...")
        
        # Load from config file
        config_locations = {}
        config_data = load_config().get("locations", {})
        for name, coord_str in config_data.items():
            if self.is_valid_coordinate(coord_str):
                lat, lon = map(float, coord_str.split(","))
                config_locations[name] = Location(name, lat, lon)
        
        # Load sensitive locations from environment if requested
        if include_sensitive:
            for key, value in VARS.items():
                if self.is_valid_coordinate(value):
                    lat, lon = map(float, value.split(","))
                    config_locations[key] = Location(key, lat, lon)
        
        logger.debug("Locations loaded successfully.")
        return config_locations
    
    def save_location(self, location: Location) -> None:
        """Saves a location to the configuration file."""
        logger.debug(f"Saving location: {location.name}...")
        configuration = load_config()
        configuration.setdefault("locations", {})[location.name] = location.to_coord_string()
        save_config(configuration)
        logger.debug(f"{location.name} location saved successfully.")
    
    def delete_location(self, location_name: str) -> bool:
        """Delete a location from saved locations."""
        try:
            config = load_config()
            if location_name in config.get("locations", {}):
                del config["locations"][location_name]
                save_config(config)
                logger.debug(f"Location '{location_name}' deleted successfully.")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting location '{location_name}': {e}")
            raise CLIWeatherException(f"Error deleting location: {e}")
    
    def get_current_location(self) -> Location:
        """Get approximate current location using IP geolocation."""
        logger.debug("Getting current location...")
        try:
            # Use IP-based geolocation to get approximate current location
            ip_geolocation_url = "https://ipinfo.io/json"
            response = requests.get(ip_geolocation_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            lat, lon = map(float, data["loc"].split(","))
            
            try:
                # Use reverse geocoding to refine location details
                location_result = self.geolocator.reverse((lat, lon), exactly_one=True)
                address = location_result.address if location_result else "Approximate location based on IP"
                return Location("Current location", lat, lon, address)
            except (GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError) as e:
                logger.warning(f"Reverse geocoding failed: {e}")
                return Location("Current location", lat, lon, "Approximate location based on IP")
                
        except requests.exceptions.Timeout as e:
            logger.error(f"Error getting current location from IP, Connection timed out: {e}")
            raise CLIWeatherException(
                "Failed to get your current location, Request timed out. Please check your network connection."
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Error getting current location from IP, Connection error: {e}")
            raise CLIWeatherException(
                "Failed to get your current location, Network error. Please check your connection and try again."
            )
        except (requests.exceptions.RequestException, JSONDecodeError) as e:
            logger.exception(f"Error Getting current location: {e}")
            raise CLIWeatherException("Could not get current location.")
    
    def geocode_address(self, address: str) -> Location:
        """Geocode an address to get location coordinates."""
        logger.debug(f"Getting location for: {address}")
        try:
            location_result = self.geolocator.geocode(address)
            if location_result:
                return Location(
                    name=address,
                    latitude=location_result.latitude,
                    longitude=location_result.longitude,
                    address=location_result.address
                )
            else:
                logger.error(f"Geolocator could not find location: '{address}'")
                raise CLIWeatherException(f"Could not find location: '{address}'")
        except GeocoderTimedOut as e:
            logger.error(f"Failed to find location: {address} geocoder timedout: {e}")
            raise CLIWeatherException(f"Failed to find {address}. Geocoding timed out.")
        except GeocoderUnavailable as e:
            logger.error(f"Failed to find location: {address} Geocoder unavailable: {e}")
            raise CLIWeatherException(f"Failed to find {address}. Geocoding service unavailable.")
        except GeocoderServiceError as e:
            logger.error(f"Failed to find {address} Geocoding service Error: {e}")
            raise CLIWeatherException(f"Failed to find {address} Geocoding service error.")
        except GeocoderParseError as e:
            logger.error(f"Failed to parse geocoding response: {e}")
            raise CLIWeatherException("Failed to parse geocoding response.")
        except Exception as e:
            logger.exception(f"Unexpected geocoding error: {e}")
            raise CLIWeatherException(f"Unexpected error occurred during geocoding: {e}")
    
    def search_locations(self, query: str) -> List[Location]:
        """Search for locations matching a query."""
        try:
            locations = self.geolocator.geocode(query, exactly_one=False, limit=5)
            if locations:
                return [
                    Location(
                        name=loc.address,
                        latitude=loc.latitude,
                        longitude=loc.longitude,
                        address=loc.address
                    ) for loc in locations
                ]
            return []
        except Exception as e:
            logger.error(f"Error searching locations: {e}")
            raise CLIWeatherException(f"Error searching locations: {e}")
    
    def validate_coordinates(self, lat: float, lon: float) -> bool:
        """Validate latitude and longitude values."""
        return -90 <= lat <= 90 and -180 <= lon <= 180
