import unittest
import json
from pathlib import Path
from unittest.mock import patch, mock_open
from datetime import datetime, timedelta

from cli_weather.core.weather import (
    fetch_weather_data,
    parse_weather_data,
    filter_best_days,
    save_weather_to_file,
    display_grouped_forecast,
)
from cli_weather.utils import CacheManager, CLIWeatherException
import requests

from cli_weather.core.location import (
    load_locations,
    is_valid_location,
    get_location,
    save_location,
    view_locations,
)
from cli_weather.config import load_config, save_config, CONFIG_FILE
from cli_weather.core.activity import (
    save_activity,
    get_activity_criteria,
    view_activities,
    choose_activity,
)

# Sample test data
SAMPLE_WEATHER_DATA = {
    "list": [
        {
            "dt": 1678886400,
            "main": {"temp": 15.5},
            "weather": [{"description": "clear sky"}],
            "wind": {"speed": 5},
            "rain": {"3h": 0},
        }
    ]
    * 40
}

SAMPLE_CONFIG_DATA = {
    "locations": {
        "London": "51.5074, 0.1278",
        "New York": "40.7128, -74.0060",
    },
    "activities": {
        "hiking": {
            "temp_min": 10,
            "temp_max": 25,
            "rain": 0,
            "wind_min": 0,
            "wind_max": 15,
            "time_range": ["06:00", "18:00"],
        }
    },
}


class TestWeather(unittest.TestCase):
    def setUp(self):
        self.cache_dir = Path("./test_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache = CacheManager(self.cache_dir, timedelta(minutes=30))

    def tearDown(self):
        for file in self.cache_dir.iterdir():
            file.unlink()
        self.cache_dir.rmdir()

    @patch("cli_weather.core.weather.requests.get")
    def test_fetch_weather_data_cached(self, mock_get):
        key = self.cache._generate_key(0, 0, "5-day")
        self.cache.save(key, SAMPLE_WEATHER_DATA)
        data = fetch_weather_data(0, 0, "dummy_key", self.cache)
        self.assertEqual(data, SAMPLE_WEATHER_DATA)
        mock_get.assert_not_called()

    @patch("cli_weather.core.weather.requests.get")
    def test_fetch_weather_data_api(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_WEATHER_DATA

        data = fetch_weather_data(0, 0, "dummy_key", self.cache)
        mock_get.assert_called_once()
        self.assertEqual(data, SAMPLE_WEATHER_DATA)

        cache_files = list(self.cache_dir.iterdir())
        self.assertEqual(len(cache_files), 1)
        with open(cache_files[0], "r") as f:
            cached_data = json.load(f)
        timestamp = datetime.fromisoformat(cached_data["timestamp"])
        self.assertLessEqual(datetime.now() - timestamp, timedelta(minutes=30))
        self.assertEqual(cached_data["data"], SAMPLE_WEATHER_DATA)

    @patch("cli_weather.core.weather.requests.get")
    def test_fetch_weather_data_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout
        with self.assertRaisesRegex(CLIWeatherException, "Request timed out"):
            fetch_weather_data(0, 0, "dummy_key", self.cache)

    def test_parse_weather_data_current(self):
        current_weather = parse_weather_data(
        SAMPLE_WEATHER_DATA["list"][0], forecast_type="current"
    )
        self.assertEqual(current_weather["temp"], 15.5)
        self.assertEqual(current_weather["weather"], "clear sky")
        self.assertEqual(current_weather["wind_speed"], 18.0)  # Match SAMPLE_WEATHER_DATA
        self.assertEqual(current_weather["rain"], 0)

    @patch("cli_weather.config.open", new_callable=mock_open, read_data=json.dumps(SAMPLE_CONFIG_DATA))
    def test_save_activity_no_config_change(self, mock_file):
        with patch("cli_weather.core.activity.load_config", return_value=SAMPLE_CONFIG_DATA):
            with patch("cli_weather.core.activity.save_config") as mock_save_config:
                save_activity(
                    "swimming",
                    {
                        "temp_min": 20,
                        "temp_max": 30,
                        "rain": 0,
                        "wind_min": 0,
                        "wind_max": 10,
                        "time_range": ["09:00", "17:00"],
                    },
                )
                mock_save_config.assert_called_once()
        mock_file.assert_not_called()


class TestLocation(unittest.TestCase):
    @patch("cli_weather.config.open", new_callable=mock_open, read_data=json.dumps(SAMPLE_CONFIG_DATA))
    def test_save_location_no_config_change(self, mock_file):
        with patch("cli_weather.core.location.load_config", return_value=SAMPLE_CONFIG_DATA):
            with patch("cli_weather.core.location.save_config") as mock_save_config:
                save_location("Test Location", "10.0, 20.0")
                mock_save_config.assert_called_once()
        mock_file.assert_not_called()


if __name__ == "__main__":
    unittest.main()