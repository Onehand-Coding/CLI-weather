import unittest
import json
import os
from pathlib import Path
from unittest.mock import patch, mock_open
from datetime import datetime, timedelta

import requests

from cli_weather.core.location import (
    load_locations, is_valid_location, get_location,
    save_location, choose_location, search_location,
    view_locations, save_current_location, delete_location
)
from cli_weather.core.activity import (
    save_activity, get_criteria, choose_activity,
    view_activities, add_activity, edit_activity,
    delete_activity
)
from cli_weather.core.weather import (
    fetch_weather_data, parse_weather_data,
    filter_best_days, display_grouped_forecast,
    save_weather_to_file, view_5day,
    view_best_activity_day, view_current,
    view_hourly, view_certain_day,
    view_oncurrent_location, fetch_typhoon_data,
    view_typhoon_tracker
)
from cli_weather.config import (
    API_KEY, LOCAL_TIMEZONE, CONFIG_FILE,
    CACHE_EXPIRY, load_config, save_config
)

from cli_weather.utils import (
    CLIWeatherException, CacheManager, confirm, get_index,
    choose_local_path, run_menu, clear_logs
)


# Sample test data
SAMPLE_CONFIG_DATA = {
    "locations": {
        "London": "51.5074, 0.1278",
        "New York": "40.7128, -74.0060"
    },
    "activities": {
        "hiking": {
            "temp_min": 10,
            "temp_max": 25,
            "rain": 0,
            "wind_min": 0,
            "wind_max": 15,
            "time_range": ["06:00", "18:00"]
        }
    }
}

SAMPLE_WEATHER_DATA = {
    "list": [
        {
            "dt": 1678886400,  # Example timestamp
            "main": {"temp": 15.5},
            "weather": [{"description": "clear sky"}],
            "wind": {"speed": 5},
            "rain": {"3h": 0}
        }
    ] * 40
}

class TestLocation(unittest.TestCase):

    def test_load_locations(self):
        # Mock the load_config function
        with patch('cli_weather.core.location.load_config') as mock_load_config:
            mock_load_config.return_value = SAMPLE_CONFIG_DATA
            locations = load_locations()
            self.assertEqual(locations, SAMPLE_CONFIG_DATA["locations"])

    def test_is_valid_location(self):
        self.assertTrue(is_valid_location("10.0, 20.0"))
        self.assertFalse(is_valid_location("abc, def"))

# ... (More tests for other functions in a similar structure)

class TestActivity(unittest.TestCase):
    """Tests for activity functions."""

class TestWeather(unittest.TestCase):
    @patch('cli_weather.core.weather.requests.get')  # Mock requests.get
    def test_fetch_weather_data_cached(self, mock_get):
        # Test using cached data

        cache = CacheManager(Path("./test_cache"), timedelta(minutes=30)) # Cache for testing
        os.mkdir("./test_cache") # Make a test cache dir
        cache.save("test_key", SAMPLE_WEATHER_DATA)

        data = fetch_weather_data(0, 0, 'dummy_key', cache)
        self.assertEqual(data, SAMPLE_WEATHER_DATA)
        os.remove("./test_cache/test_key")
        os.rmdir("./test_cache")
        mock_get.assert_not_called()  # requests.get should not be called

    @patch('cli_weather.core.weather.requests.get') # Mock requests.get
    def test_fetch_weather_data_api(self, mock_get):
        # Test fetching from API
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_WEATHER_DATA


        cache = CacheManager(Path("./test_cache"), timedelta(minutes=30))
        os.mkdir("./test_cache")


        data = fetch_weather_data(0, 0, 'dummy_key', cache)

        cache_files = list(Path("./test_cache").iterdir())
        self.assertEqual(len(cache_files), 1)  # There should be a cached file now
        with open(cache_files[0], 'r') as f: # cleanup
            cached_data = json.load(f)
        os.remove(cache_files[0])
        os.rmdir("./test_cache")

        mock_get.assert_called_once() # request.get should be called once
        self.assertEqual(data, SAMPLE_WEATHER_DATA)
        # check if timestamp and data match to SAMPLE_WEATHER_DATA.
        timestamp = datetime.fromisoformat(cached_data["timestamp"])
        self.assertLessEqual(datetime.now() - timestamp, CACHE_EXPIRY)
        self.assertEqual(cached_data["data"], SAMPLE_WEATHER_DATA)

    @patch('cli_weather.core.weather.requests.get')
    def test_fetch_weather_data_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout
        cache = CacheManager(Path("./test_cache"), timedelta(minutes=30))  # Dummy cache
        with self.assertRaisesRegex(CLIWeatherException, "Request timed out"):
            fetch_weather_data(0, 0, "dummy_key", cache)

# ... More tests for Weather functions, including error handling cases



if __name__ == '__main__':
    unittest.main()