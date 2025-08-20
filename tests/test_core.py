import json
import unittest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open

import requests
import geopy.exc

from cli_weather.legacy.config import load_config, save_config, CONFIG_FILE
from cli_weather.legacy.utils import CacheManager, CLIWeatherException, choose_local_path
from cli_weather.legacy.weather import (
    fetch_weather_data,
    parse_weather_data,
    filter_best_days,
    save_weather_to_file,
    display_grouped_forecast,
    fetch_typhoon_data,
    view_typhoon_tracker,
)
from cli_weather.legacy.location import (
    load_locations,
    is_valid_location,
    get_location,
    save_location,
    view_locations,
)
from cli_weather.legacy.activity import (
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
    "locations": {"London": "51.5074, 0.1278", "New York": "40.7128, -74.0060"},
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

    @patch("cli_weather.legacy.weather.requests.get")
    def test_fetch_weather_data_cached(self, mock_get):
        key = self.cache._generate_key(0, 0, "5-day")
        self.cache.save(key, SAMPLE_WEATHER_DATA)
        data = fetch_weather_data(0, 0, "dummy_key", self.cache)
        self.assertEqual(data, SAMPLE_WEATHER_DATA)
        mock_get.assert_not_called()

    @patch("cli_weather.legacy.weather.requests.get")
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

    @patch("cli_weather.legacy.weather.requests.get")
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
        self.assertEqual(current_weather["wind_speed"], 18.0)
        self.assertEqual(current_weather["rain"], 0)

    def test_parse_weather_data_hourly(self):
        hourly_weather = parse_weather_data(SAMPLE_WEATHER_DATA, forecast_type="hourly")
        self.assertEqual(
            len(hourly_weather), 24
        )  # Check if it parses data for next 24 hours
        # Add assertions for individual hourly data points as needed

    def test_parse_weather_data_5day(self):
        daily_weather = parse_weather_data(SAMPLE_WEATHER_DATA, forecast_type="5-day")
        self.assertEqual(len(daily_weather), 5)  # Check if 5 days are parsed
        # Add assertions for individual daily data points as needed

    # Implement your test for filter_best_days. Uncomment when ready. You will need to mock config.load_config().
    # def test_filter_best_days(self):
    #    with patch("cli_weather.weather.load_config") as mock_load_config:
    #        mock_load_config.return_value = { # Ensure to add relevant activity data here to match to SAMPLE_WEATHER_DATA
    #            "activities": {

    #            }
    #        }
    #        daily_weather = parse_weather_data(SAMPLE_WEATHER_DATA)
    #        hourly_weather = parse_weather_data(SAMPLE_WEATHER_DATA, forecast_type="hourly")

    #        best_days = filter_best_days(daily_weather, "hiking", hourly_weather) # Ensure hiking is defined in your mock config.

    @patch("cli_weather.legacy.weather.open", new_callable=mock_open)
    @patch("cli_weather.legacy.weather.choose_local_path")  # Adjusted patch path
    @patch("cli_weather.legacy.utils.confirm")
    @patch("cli_weather.legacy.utils.get_index")
    def test_save_weather_to_file(
        self, mock_get_index, mock_confirm, mock_choose_local_path, mock_file
    ):
        mock_get_index.return_value = 0
        mock_confirm.return_value = True
        mock_choose_local_path.return_value = self.cache_dir

        sample_weather = [
            {
                "date": "2024-04-02",
                "temp": 15,
                "weather": "Cloudy",
                "wind_speed": 5,
                "rain": 0,
            }
        ]

        save_weather_to_file("London", sample_weather)

        expected_file = self.cache_dir / "London_weather.txt"
        mock_file.assert_called_once_with(expected_file, "w")

    @patch("cli_weather.legacy.weather.print")  # Mock 'print' to capture output
    def test_display_grouped_forecast(self, mock_print):
        sample_forecast = [
            {
                "date": "2024-04-02 09:00:00",
                "temp": 15,
                "weather": "Cloudy",
                "wind_speed": 5,
                "rain": 0,
            },
            {
                "date": "2024-04-02 12:00:00",
                "temp": 17,
                "weather": "Sunny",
                "wind_speed": 7,
                "rain": 0.5,
            },
        ]
        display_grouped_forecast(sample_forecast, forecast_type="hourly")

        # Example assertion to check if summary is printed
        mock_print.assert_any_call(
            "  Summary: Avg Temp: 16.00°C, Total Rain: 0.50 mm, Wind Range: 5.00-7.00 km/h"
        )


class TestLocation(unittest.TestCase):
    @patch("cli_weather.legacy.location.load_config")
    def test_load_locations(self, mock_load_config):
        mock_load_config.return_value = SAMPLE_CONFIG_DATA
        locations = load_locations()
        self.assertEqual(locations, SAMPLE_CONFIG_DATA["locations"])

        mock_load_config.return_value = {"activities": {}}  # No locations in config
        self.assertEqual(load_locations(), {})

    def test_is_valid_location(self):
        self.assertTrue(is_valid_location("10.0, 20.0"))
        self.assertFalse(is_valid_location("abc, def"))
        self.assertFalse(is_valid_location("91,0, 10"))  # invalid coordinate
        self.assertFalse(is_valid_location("50.2, 181"))  # Invalid coordinate

    @patch("cli_weather.legacy.location.Nominatim")
    @patch("cli_weather.legacy.location.requests.get")
    def test_get_location_current(self, mock_requests_get, mock_nominatim):
        # mocking current location data from ipinfo.io
        mock_response = mock_requests_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {"loc": "12.34,56.78", "city": "Test City"}

        # Mock geolocator
        mock_geolocator = mock_nominatim.return_value
        mock_geolocator.reverse.return_value.address = "Test Address"  # Mock address

        address, lat, lon = get_location("me")
        self.assertEqual(address, "Test Address")
        self.assertEqual(lat, 12.34)
        self.assertEqual(lon, 56.78)

        # Test approximate location if reverse geocoding fails
        mock_geolocator.reverse.return_value = (
            None  # Simulate reverse geocoding failure
        )
        address, lat, lon = get_location("me")
        self.assertEqual(address, "Approximate location based on IP")
        self.assertEqual(lat, 12.34)
        self.assertEqual(lon, 56.78)

    @patch("cli_weather.legacy.location.Nominatim")
    def test_get_location_address(self, MockNominatim):
        geolocator_mock = MockNominatim.return_value
        geolocator_mock.geocode.return_value.address = "123 Main St, Anytown"
        geolocator_mock.geocode.return_value.latitude = 34.56
        geolocator_mock.geocode.return_value.longitude = -78.90

        self.assertEqual(
            get_location("Anytown"), ("123 Main St, Anytown", 34.56, -78.90)
        )

        geolocator_mock.geocode.return_value = None  # Simulate location not found
        with self.assertRaisesRegex(
            CLIWeatherException, "Could not find location: 'Unknown Place'"
        ):
            get_location("Unknown Place")

    def test_save_location(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_config_path = Path(temp_dir) / "config.json"
            with open(temp_config_path, "w") as f:
                json.dump(SAMPLE_CONFIG_DATA, f)

            with patch(
                "cli_weather.legacy.config.CONFIG_FILE", temp_config_path
            ):  # Patch CONFIG_FILE
                save_location("My Location", "1.23, 4.56")

                # Check the updated config
                updated_config = json.loads(temp_config_path.read_text())
                self.assertEqual(
                    updated_config["locations"]["My Location"], "1.23, 4.56"
                )

    @patch("builtins.print")
    @patch("cli_weather.legacy.location.load_locations")
    def test_view_locations(self, mock_load_locations, mock_print):
        # Test case 1: Locations exist
        mock_load_locations.return_value = SAMPLE_CONFIG_DATA["locations"]
        view_locations()
        mock_print.assert_any_call("\nYour Locations:\n")  # Use assert_any_call

        # Reset the mock
        mock_print.reset_mock()

        # Test case 2: No locations
        mock_load_locations.return_value = {}  # No Locations case
        view_locations()
        mock_print.assert_called_with("No locations found. Please add one first.")


class TestActivity(unittest.TestCase):
    # Mock necessary functions and data where required.

    @patch("cli_weather.legacy.activity.open", mock_open())
    def test_save_activity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_config_path = Path(temp_dir) / "config.json"
            with open(temp_config_path, "w") as f:
                json.dump(SAMPLE_CONFIG_DATA, f)

            with patch("cli_weather.legacy.config.CONFIG_FILE", temp_config_path):
                new_activity = {
                    "temp_min": 20,
                    "temp_max": 30,
                    "rain": 0,
                    "wind_min": 0,
                    "wind_max": 10,
                    "time_range": ["09:00", "17:00"],
                }
                save_activity("swimming", new_activity)

                updated_config = json.loads(temp_config_path.read_text())
                self.assertEqual(updated_config["activities"]["swimming"], new_activity)

    @patch(
        "builtins.input",
        side_effect=["hiking", "15", "25", "2", "10", "n", "y", "10", "y", "y"],
    )
    def test_get_activity_criteria(self, mock_input):
        criteria = get_activity_criteria("hiking")
        self.assertEqual(criteria["temp_min"], 15)

    @patch("cli_weather.legacy.activity.load_config")  # Mock config data
    @patch("builtins.print")  # Mock print
    def test_view_activities(self, mock_print, mock_load_config):
        # Test case 1: Activities exist
        mock_load_config.return_value = {"activities": SAMPLE_CONFIG_DATA["activities"]}
        view_activities()
        mock_print.assert_any_call("\nYour Activities:\n")  # Use assert_any_call

        # Reset the mock for the next test case
        mock_print.reset_mock()

        # Test case 2: No activities
        mock_load_config.return_value = {"activities": {}}  # No activities case.
        view_activities()
        mock_print.assert_called_with(
            "No activities found. Please add an activity first."
        )

    @patch("cli_weather.legacy.activity.load_config")
    @patch(
        "builtins.input", side_effect=["1"]
    )  # Mocking user input to choose the first option
    @patch("builtins.print")  # Mock print
    def test_choose_activity(self, mock_print, mock_input, mock_config):
        mock_config.return_value = {"activities": SAMPLE_CONFIG_DATA["activities"]}

        activity = choose_activity()
        self.assertEqual(activity, "hiking")

        mock_config.return_value = {"activities": {}}  # Test with no activities
        choose_activity()  # Should print message and return
        mock_print.assert_called_with(
            "No activities found. Please add an activity first."
        )


class TestTyphoonTracking(unittest.TestCase):
    """Test cases for typhoon tracking functionality."""

    def setUp(self):
        """Set up test environment."""
        self.api_key = "test_api_key"
        self.lat = 14.5987713
        self.lon = 120.9833966
        self.mock_response = {
            "alerts": [
                {
                    "event": "Typhoon Warning",
                    "severity": "severe",
                    "start": "2024-03-20T00:00:00Z",
                    "end": "2024-03-21T00:00:00Z",
                    "description": "Typhoon approaching the area",
                }
            ],
            "current": {"temp": 25.5, "humidity": 80},
            "timezone": "Asia/Manila",
        }

    @patch("requests.get")
    def test_fetch_typhoon_data_success(self, mock_get):
        """Test successful typhoon data fetching."""
        mock_get.return_value.json.return_value = self.mock_response
        mock_get.return_value.raise_for_status.return_value = None

        result = fetch_typhoon_data(self.api_key, self.lat, self.lon)

        self.assertEqual(result["alerts"], self.mock_response["alerts"])
        self.assertEqual(result["current"], self.mock_response["current"])
        self.assertEqual(result["timezone"], self.mock_response["timezone"])

    @patch("requests.get")
    def test_fetch_typhoon_data_error(self, mock_get):
        """Test error handling in typhoon data fetching."""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        with self.assertRaises(CLIWeatherException):
            fetch_typhoon_data(self.api_key, self.lat, self.lon)

    @patch("cli_weather.legacy.weather.fetch_typhoon_data")
    @patch("cli_weather.legacy.weather.choose_location")
    @patch("builtins.input")  # Mock input to prevent stdin reading
    def test_view_typhoon_tracker_with_alerts(
        self, mock_input, mock_choose_location, mock_fetch_data
    ):
        """Test viewing typhoon tracker with active alerts."""
        mock_choose_location.return_value = ("Manila", (self.lat, self.lon))
        mock_fetch_data.return_value = self.mock_response
        mock_input.return_value = "n"  # Respond 'no' to save prompt

        with patch("builtins.print") as mock_print:
            view_typhoon_tracker()
            mock_print.assert_any_call("\nWeather Alerts for Manila:")
            mock_print.assert_any_call("Alert: Typhoon Warning")

    @patch("cli_weather.legacy.weather.fetch_typhoon_data")
    @patch("cli_weather.legacy.weather.choose_location")
    def test_view_typhoon_tracker_no_alerts(
        self, mock_choose_location, mock_fetch_data
    ):
        """Test viewing typhoon tracker with no active alerts."""
        mock_choose_location.return_value = ("Manila", (self.lat, self.lon))
        mock_fetch_data.return_value = {"alerts": [], "current": {}, "timezone": "UTC"}

        with patch("builtins.print") as mock_print:
            view_typhoon_tracker()
            mock_print.assert_any_call(
                "No active weather alerts or typhoons in this area."
            )


if __name__ == "__main__":
    unittest.main()
