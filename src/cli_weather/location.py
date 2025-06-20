"""Location management functions."""

import logging
from typing import Dict, Tuple
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

from .config import VARS, load_config, save_config
from .utils import CLIWeatherException, confirm, choose

logger = logging.getLogger(__file__)


# === Location management functions === #
def load_locations(add_sensitive: bool = False) -> Dict:
    """Loads location data from config and optionally from environment variables."""
    logger.debug("Loading locations...")
    non_sensitive_locations = load_config().get("locations", {})
    sensitive_locations = {
        key: value for key, value in VARS.items() if is_valid_location(value)
    }
    locations = (
        {**sensitive_locations, **non_sensitive_locations}
        if add_sensitive
        else non_sensitive_locations
    )

    logger.debug("Locations loaded successfully.")
    return locations


def is_valid_location(value: str) -> bool:
    """Checks if a given string represents valid latitude/longitude coordinates."""
    try:
        logger.debug(f"Checking if '{value}' is valid location coordinate.")
        lat, lon = map(float, value.split(","))
        return -90 <= lat <= 90 and -180 <= lon <= 180
    except (ValueError, TypeError):
        return False


def get_location(
    addr: str = "me",
) -> Tuple[str, float, float] | Tuple[None, None, None]:
    """Get location by address or approximate current location."""
    geopy.adapters.BaseAdapter.session = requests.Session()

    if addr.lower() == "me":  # Handle current location separately
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
                geolocator = Nominatim(user_agent="weather_assistant", timeout=10)
                location = geolocator.reverse((lat, lon), exactly_one=True)
                address = (
                    location.address if location else "Approximate location based on IP"
                )
                return address, lat, lon
            except (GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError) as e:
                logger.warning(f"Reverse geocoding failed: {e}")
                return "Approximate location based on IP", lat, lon

        except requests.exceptions.Timeout as e:
            logger.error(
                f"Error getting current location from IP, Connection timed out: {e}"
            )
            raise CLIWeatherException(
                "Failed to get your current location, Request timed out. Please check your network connection."
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(
                f"Error getting current location from IP, Connection error: {e}"
            )
            raise CLIWeatherException(
                "Failed to get your current location, Network error. Please check your connection and try again."
            )
        except (requests.exceptions.RequestException, JSONDecodeError) as e:
            logger.exception(f"Error Getting current location: {e}")
            raise CLIWeatherException("Could not get current location.")

    else:  # Use Geopy for address-based geocoding
        logger.debug(f"Getting location for: {addr}")
        try:
            geolocator = Nominatim(user_agent="weather_assistant", timeout=10)
            location = geolocator.geocode(addr)
            if location:
                return location.address, location.latitude, location.longitude
            else:
                logger.error(f"Geolocator could not find location: '{addr}'")
                raise CLIWeatherException(f"Could not find location: '{addr}'")
        except GeocoderTimedOut as e:
            logger.error(f"Failed to find location: {addr} geocoder timedout: {e}")
            raise CLIWeatherException(f"Failed to find {addr}. Geocoding timed out.")
        except GeocoderUnavailable as e:
            logger.error(f"Failed to find location: {addr} Geocoder unavailable: {e}")
            raise CLIWeatherException(
                f"Failed to find {addr}. Geocoding service unavailable."
            )
        except GeocoderServiceError as e:
            logger.error(f"Failed to find {addr} Geocoding service Error: {e}")
            raise CLIWeatherException(f"Failed to find {addr} Geocoding service error.")
        except GeocoderParseError as e:
            logger.error(f"Failed to parse geocoding response: {e}")
            raise CLIWeatherException("Failed to parse geocoding response.")
        except Exception as e:
            logger.exception(f"Unexpected geocoding error: {e}")
            raise CLIWeatherException(
                f"Unexpected error occurred during geocoding: {e}"
            )


def get_location_input() -> Tuple[str, str]:
    """Gets location name and coordinates input from the user."""
    try:
        while True:
            location_name = input("Enter location name: ")
            print(
                "Enter comma separated coordinates Lat/Long (Deg), e.g., 1.599, 12.6168"
            )
            coordinate = input("> ")
            if is_valid_location(coordinate) and confirm("Done?"):
                return (location_name, coordinate)
    except KeyboardInterrupt:
        raise


def save_location(location_name: str, coordinate: str) -> None:
    """Saves a location into configuration file."""
    logger.debug(f"Saving location : {location_name}...")
    configuration = load_config()
    configuration.setdefault("locations", {})[location_name] = coordinate
    save_config(configuration)
    logger.debug(f"{location_name} location saved successfully.")


def choose_location(
    task: str = "",
    *,
    add_sensitive: bool = False,
    add_search: bool = False,
    add_current: bool = False,
) -> Tuple[str, Tuple[str, str]] | None:
    """Prompt the user to choose a location from the saved locations."""
    locations = load_locations(add_sensitive)
    if not locations:
        print("No locations found. Please add one first.")
        return
    # Add choice to use current location.
    if add_current:
        locations["Current location"] = "N, A"
    # Add choice to search for a location using an address.
    if add_search:
        locations["Search location"] = "N, A"
    # Add choice to go back from previous menu.
    locations["Back"] = "N, A"
    print(
        f"\nChoose a location {task}."
        if not add_search
        else f"Choose or search a location {task}."
    )
    location_name = choose(list(locations))
    lat, lon = locations[location_name].split(",")
    return location_name, (lat.strip(), lon.strip())


def search_location() -> None:
    """Allow user to search for a location and save it."""
    search_query = input("Enter location to search: ")
    try:  # Catching custom exception early here to prevent getting out of manage locations menu early.
        address, lat, lon = get_location(search_query)
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return

    if all((address, lat, lon)):
        print(f"Address found: {address}")
        if confirm("Save this location?"):
            location_name = input("Enter a name for this location: ").strip() or address
            save_location(location_name, f"{lat}, {lon}")
            print(f"Location '{location_name}' saved successfully.")
    else:
        print("Location not found.")


def view_locations() -> None:
    """Displays the saved locations."""
    locations = load_locations()
    if not locations:
        print("No locations found. Please add one first.")
        return
    print("\nYour Locations:\n")
    for location_name, coordinate in locations.items():
        lat, lon = coordinate.split(",")
        print(f"""{location_name.title()}:
            latitude: {lat.strip()}
            longitude: {lon}""")


def add_location() -> None:
    """Adds a new location to the saved locations."""
    location_name, coordinate = get_location_input()
    if confirm(f"Save this location?\n {location_name}: {coordinate}"):
        save_location(location_name, coordinate)
        print(f"New location {location_name} saved successfully.")


def save_current_location() -> None:
    """Let user save current location."""

    try:  # Catching custom exception early here to prevent getting out of manage locations menu.
        current_addr, lat, lon = get_location()
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return

    print(f"Current location: {current_addr}:\n\tlatitude: {lat}, longitude: {lon}")
    if confirm("Do you want to rename location address?"):
        current_addr = input("Enter new name for this location: ")
    if confirm("Save this location?"):
        config = load_config()
        config["locations"][current_addr] = f"{str(lat)}, {str(lon)}"
        save_config(config)
        print("Current location saved successfully.")


def delete_location() -> None:
    """Let user delete a location from saved locations."""
    try:
        location_name, _ = choose_location(task="to delete")
    except TypeError:
        return
    # If user choose to abort deleting a location.
    if location_name == "Back":
        return
    if confirm(f"Are you sure you want to delete '{location_name}'?"):
        config = load_config()
        del config["locations"][location_name]
        save_config(config)
        print(f"\n'{location_name}' deleted successfully.")
