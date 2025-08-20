#!/usr/bin/env python
"""
Legacy main module for backwards compatibility.

This module preserves the original CLI Weather Application functionality
using the original mixed-concern architecture for users who need compatibility.
"""

import sys
import time
import logging

from .config import CACHED_DIR, LOG_DIR, CACHE_EXPIRY, configure_logging
from .utils import CLIWeatherException, CacheManager, run_menu, clear_logs
from .weather import (
    view_current,
    view_hourly,
    view_5day,
    view_certain_day,
    view_best_activity_day,
    view_typhoon_tracker,
)
from .location import (
    view_locations,
    add_location,
    save_current_location,
    search_location,
    delete_location,
)
from .activity import view_activities, add_activity, edit_activity, delete_activity

# Use caching for fetching weather data.
cache_manager = CacheManager(CACHED_DIR, CACHE_EXPIRY)

# == Menu Options == #
WEATHER_OPTIONS = [
    {"View Current Weather": lambda: view_current(cache_manager)},
    {"View Hourly Forecast": lambda: view_hourly(cache_manager)},
    {"View 5-Day Forecast": lambda: view_5day(cache_manager)},
    {"View Forecast for a Certain Day": lambda: view_certain_day(cache_manager)},
    {"View Best Day(s) for an Activity": lambda: view_best_activity_day(cache_manager)},
    {"Back": None},
]
LOCATION_OPTIONS = [
    {"View locations": lambda: view_locations()},
    {"Add a location": lambda: add_location()},
    {"Save Current Location": lambda: save_current_location()},
    {"Search a location": lambda: search_location()},
    {"Delete a location": lambda: delete_location()},
    {"Back": None},
]
ACTIVITY_OPTIONS = [
    {"View Activities": lambda: view_activities()},
    {"Add Activity": lambda: add_activity()},
    {"Edit Activity": lambda: edit_activity()},
    {"Delete Activity": lambda: delete_activity()},
    {"Back": None},
]
OTHER_OPTIONS = [
    {"Clear cached data": lambda: cache_manager.clear()},
    {"Clear logs": lambda: clear_logs(LOG_DIR)},
    {"Back": None},
]
MAIN_OPTIONS = [
    {
        "View Weather Forecasts": lambda: run_menu(
            WEATHER_OPTIONS, "View Weather Forecasts"
        )
    },
    {"Manage Locations": lambda: run_menu(LOCATION_OPTIONS, "Manage Locations")},
    {"Manage Activities": lambda: run_menu(ACTIVITY_OPTIONS, "Manage Activities")},
    {"Track Typhoons": lambda: view_typhoon_tracker()},
    {"Other Options": lambda: run_menu(OTHER_OPTIONS, "OTHER OPTIONS")},
    {"Exit": None},
]


def legacy_main() -> None:
    """
    Legacy main function to run the CLI Weather Application.

    Configures logging, displays the welcome message, and enters the main menu loop.
    Handles exceptions and keyboard interrupts gracefully.
    """
    configure_logging()
    logging.debug("Legacy app started.")
    print("\nWelcome to CLI Weather Assistant! (Legacy Mode)")
    while True:
        try:
            run_menu(MAIN_OPTIONS, "MAIN OPTIONS", main=True)
        except CLIWeatherException as e:
            print(f"Error: {e}")
        except KeyboardInterrupt:
            logging.debug("App interrupted.")
            print("\nExiting...")
            time.sleep(0.5)
            print("Goodbye!")
            sys.exit()
        except Exception as e:
            logging.exception(f"An unexpected error occurred: {e}")
            print(f"An unexpected error occurred: {e}")
            sys.exit(1)


if __name__ == "__main__":
    legacy_main()
