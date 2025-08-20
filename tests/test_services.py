"""
Comprehensive tests for the separated business logic services.

This module tests the core business logic services with proper mocking,
ensuring separation of concerns and reliability of the new architecture.
"""

import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open, MagicMock, Mock

import requests
import geopy.exc

from cli_weather.core.app import WeatherApp
from cli_weather.core.models import Location as ModelsLocation, Activity as ModelsActivity
from cli_weather.core.weather_service import WeatherService, WeatherData
from cli_weather.core.location_service import LocationService, Location
from cli_weather.core.activity_service import ActivityService, Activity
from cli_weather.core.config_service import ConfigService
from cli_weather.core.cache_service import CacheService
from cli_weather.core.exceptions import WeatherAppError, WeatherAPIError, LocationError
from cli_weather.legacy.utils import CacheManager


class TestWeatherService(unittest.TestCase):
    """Test the WeatherService class."""
    
    def setUp(self):
        """Set up test environment."""
        self.cache_manager = MagicMock(spec=CacheManager)
        self.weather_service = WeatherService("test_api_key", self.cache_manager)
        
        # Sample weather API response
        self.sample_api_response = {
            "list": [
                {
                    "dt": 1678886400,
                    "main": {"temp": 15.5},
                    "weather": [{"description": "clear sky"}],
                    "wind": {"speed": 5},
                    "rain": {"3h": 0},
                }
            ] * 40
        }
        
        self.sample_current_response = {
            "dt": 1678886400,
            "main": {"temp": 15.5},
            "weather": [{"description": "clear sky"}],
            "wind": {"speed": 5},
            "rain": {"1h": 0},
        }
    
    @patch('cli_weather.core.weather_service.requests.get')
    def test_fetch_weather_data_from_cache(self, mock_get):
        """Test fetching weather data from cache."""
        # Setup cache to return data
        self.cache_manager.load.return_value = self.sample_api_response
        
        result = self.weather_service.fetch_weather_data(0, 0, "5-day")
        
        self.assertEqual(result, self.sample_api_response)
        self.cache_manager.load.assert_called_once()
        mock_get.assert_not_called()
    
    @patch('cli_weather.core.weather_service.requests.get')
    def test_fetch_weather_data_from_api(self, mock_get):
        """Test fetching weather data from API."""
        # Setup cache to return None (no cached data)
        self.cache_manager.load.return_value = None
        
        # Setup mock response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = self.sample_api_response
        mock_get.return_value = mock_response
        
        result = self.weather_service.fetch_weather_data(0, 0, "5-day")
        
        self.assertEqual(result, self.sample_api_response)
        mock_get.assert_called_once()
        self.cache_manager.save.assert_called_once()
    
    @patch('cli_weather.core.weather_service.requests.get')
    def test_fetch_weather_data_api_error(self, mock_get):
        """Test API error handling."""
        self.cache_manager.load.return_value = None
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        with self.assertRaises(Exception):  # Using generic Exception for now since the actual service uses legacy exception
            self.weather_service.fetch_weather_data(0, 0, "5-day")
    
    def test_parse_current_weather(self):
        """Test parsing current weather data."""
        weather = self.weather_service.parse_current_weather(self.sample_current_response)
        
        self.assertIsInstance(weather, WeatherData)
        self.assertEqual(weather.temp, 15.5)
        self.assertEqual(weather.weather, "clear sky")
        self.assertEqual(weather.wind_speed, 18.0)  # 5 m/s * 3.6 = 18 km/h
        self.assertEqual(weather.rain, 0)
    
    def test_parse_hourly_weather(self):
        """Test parsing hourly weather data."""
        forecast = self.weather_service.parse_hourly_weather(self.sample_api_response)
        
        self.assertEqual(len(forecast), 24)  # Default 24 hours
        self.assertIsInstance(forecast[0], WeatherData)
    
    def test_parse_daily_weather(self):
        """Test parsing daily weather data."""
        forecast = self.weather_service.parse_daily_weather(self.sample_api_response)
        
        self.assertEqual(len(forecast), 5)  # 5 days
        self.assertIsInstance(forecast[0], WeatherData)
    
    @patch.object(WeatherService, 'fetch_weather_data')
    @patch.object(WeatherService, 'parse_current_weather')
    def test_get_current_weather(self, mock_parse, mock_fetch):
        """Test get_current_weather method."""
        mock_fetch.return_value = self.sample_current_response
        mock_weather = WeatherData("2023-03-15 12:00:00", 15.5, "clear sky", 18.0, 0)
        mock_parse.return_value = mock_weather
        
        result = self.weather_service.get_current_weather(40.7128, -74.0060)
        
        self.assertEqual(result, mock_weather)
        mock_fetch.assert_called_once_with(40.7128, -74.0060, "current")
        mock_parse.assert_called_once_with(self.sample_current_response)
    
    def test_filter_best_days_for_activity(self):
        """Test filtering best days for activity."""
        # Create sample weather data
        daily_weather = [
            WeatherData("2023-03-15", 20, "sunny", 10, 0),
            WeatherData("2023-03-16", 25, "cloudy", 15, 2),
        ]
        hourly_weather = []
        
        activity_criteria = {
            "temp_min": 15,
            "temp_max": 30,
            "rain": 1,
            "wind_min": 0,
            "wind_max": 20,
            "time_range": ["00:00", "23:59"]
        }
        
        result = self.weather_service.filter_best_days_for_activity(
            daily_weather, hourly_weather, activity_criteria
        )
        
        self.assertEqual(len(result), 1)  # Only first day should match (rain < 1)
        self.assertEqual(result[0].temp, 20)


class TestLocationService(unittest.TestCase):
    """Test the LocationService class."""
    
    def setUp(self):
        """Set up test environment."""
        self.location_service = LocationService()
        
        # Sample location data
        self.sample_locations = {
            "London": "51.5074, -0.1278",
            "New York": "40.7128, -74.0060"
        }
    
    @patch('cli_weather.core.location_service.load_config')
    def test_load_locations(self, mock_load_config):
        """Test loading locations from config."""
        mock_config = {"locations": self.sample_locations}
        mock_load_config.return_value = mock_config
        
        locations = self.location_service.load_locations()
        
        self.assertEqual(len(locations), 2)
        self.assertIn("London", locations)
        self.assertIsInstance(locations["London"], Location)
        self.assertEqual(locations["London"].latitude, 51.5074)
    
    def test_validate_coordinates(self):
        """Test coordinate validation."""
        self.assertTrue(self.location_service.validate_coordinates(40.7128, -74.0060))
        self.assertFalse(self.location_service.validate_coordinates(91, 0))  # Invalid lat
        self.assertFalse(self.location_service.validate_coordinates(0, 181))  # Invalid lon
    
    @patch('cli_weather.core.location_service.Nominatim')
    def test_geocode_address(self, mock_nominatim_class):
        """Test geocoding an address."""
        # Setup mock geolocator
        mock_geolocator = Mock()
        mock_location = Mock()
        mock_location.address = "New York, NY, USA"
        mock_location.latitude = 40.7128
        mock_location.longitude = -74.0060
        mock_geolocator.geocode.return_value = mock_location
        mock_nominatim_class.return_value = mock_geolocator
        
        result = self.location_service.geocode_address("New York")
        
        self.assertIsInstance(result, Location)
        self.assertEqual(result.name, "New York")  # Location name is set to the input query
        self.assertAlmostEqual(result.latitude, 40.7128, places=3)  # Use assertAlmostEqual for float precision
        self.assertAlmostEqual(result.longitude, -74.0060, places=3)
    
    @patch('cli_weather.core.location_service.Nominatim')
    def test_geocode_address_not_found(self, mock_nominatim_class):
        """Test geocoding with location not found."""
        mock_geolocator = Mock()
        mock_geolocator.geocode.return_value = None
        mock_nominatim_class.return_value = mock_geolocator
        
        with self.assertRaises(Exception):  # Using generic Exception for now since the actual service uses legacy exception
            self.location_service.geocode_address("NonexistentPlace")
    
    @patch('cli_weather.core.location_service.requests.get')
    @patch('cli_weather.core.location_service.Nominatim')
    def test_get_current_location(self, mock_nominatim_class, mock_requests_get):
        """Test getting current location via IP."""
        # Mock IP info response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"loc": "40.7128,-74.0060", "city": "New York"}
        mock_requests_get.return_value = mock_response
        
        # Mock reverse geocoding
        mock_geolocator = Mock()
        mock_reverse_result = Mock()
        mock_reverse_result.address = "New York, NY, USA"
        mock_geolocator.reverse.return_value = mock_reverse_result
        mock_nominatim_class.return_value = mock_geolocator
        
        result = self.location_service.get_current_location()
        
        self.assertIsInstance(result, Location)
        self.assertEqual(result.name, "Current location")  # Default name for current location
        self.assertEqual(result.latitude, 40.7128)
        self.assertEqual(result.longitude, -74.0060)
    
    @patch('cli_weather.core.location_service.save_config')
    @patch('cli_weather.core.location_service.load_config')
    def test_save_location(self, mock_load_config, mock_save_config):
        """Test saving a location."""
        mock_load_config.return_value = {"locations": {}}
        location = ModelsLocation("Test Location", 40.0, -74.0)
        
        self.location_service.save_location(location)
        
        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]
        self.assertIn("Test Location", saved_config["locations"])
        self.assertEqual(saved_config["locations"]["Test Location"], "40.0, -74.0")
    
    @patch('cli_weather.core.location_service.save_config')
    @patch('cli_weather.core.location_service.load_config')
    def test_delete_location(self, mock_load_config, mock_save_config):
        """Test deleting a location."""
        mock_load_config.return_value = {"locations": self.sample_locations}
        
        result = self.location_service.delete_location("London")
        
        self.assertTrue(result)
        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]
        self.assertNotIn("London", saved_config["locations"])
    
    def test_delete_nonexistent_location(self):
        """Test deleting a non-existent location."""
        with patch('cli_weather.core.location_service.load_config') as mock_load:
            mock_load.return_value = {"locations": {}}
            
            result = self.location_service.delete_location("NonExistent")
            
            self.assertFalse(result)


class TestActivityService(unittest.TestCase):
    """Test the ActivityService class."""
    
    def setUp(self):
        """Set up test environment."""
        self.activity_service = ActivityService()
        
        # Sample activity data
        self.sample_activities = {
            "hiking": {
                "temp_min": 10,
                "temp_max": 25,
                "rain": 0,
                "wind_min": 0,
                "wind_max": 15,
                "time_range": ["06:00", "18:00"]
            }
        }
    
    @patch('cli_weather.core.activity_service.load_config')
    def test_load_activities(self, mock_load_config):
        """Test loading activities from config."""
        mock_config = {"activities": self.sample_activities}
        mock_load_config.return_value = mock_config
        
        activities = self.activity_service.load_activities()
        
        self.assertEqual(len(activities), 1)
        self.assertIn("hiking", activities)
        self.assertIsInstance(activities["hiking"], Activity)
        self.assertEqual(activities["hiking"].temp_min, 10)
    
    @patch('cli_weather.core.activity_service.load_config')
    def test_get_activity(self, mock_load_config):
        """Test getting a specific activity."""
        mock_config = {"activities": self.sample_activities}
        mock_load_config.return_value = mock_config
        
        activity = self.activity_service.get_activity("hiking")
        
        self.assertIsInstance(activity, Activity)
        self.assertEqual(activity.name, "hiking")
        self.assertEqual(activity.temp_min, 10)
    
    def test_get_nonexistent_activity(self):
        """Test getting a non-existent activity."""
        with patch('cli_weather.core.activity_service.load_config') as mock_load:
            mock_load.return_value = {"activities": {}}
            
            activity = self.activity_service.get_activity("nonexistent")
            
            self.assertIsNone(activity)
    
    def test_create_activity(self):
        """Test creating a new activity."""
        activity = self.activity_service.create_activity(
            "running", 15, 28, 2.0, 25.0, 5.0, ["06:00", "20:00"]
        )
        
        self.assertIsInstance(activity, Activity)
        self.assertEqual(activity.name, "running")
        self.assertEqual(activity.temp_min, 15)
        self.assertEqual(activity.temp_max, 28)
        self.assertEqual(activity.rain, 2.0)  # It's 'rain' not 'max_rain' in the ActivityService class
        self.assertEqual(activity.wind_max, 25.0)
        self.assertEqual(activity.wind_min, 5.0)
        self.assertEqual(activity.time_range, ["06:00", "20:00"])  # It's a list not tuple
    
    @patch('cli_weather.core.activity_service.save_config')
    @patch('cli_weather.core.activity_service.load_config')
    def test_save_activity(self, mock_load_config, mock_save_config):
        """Test saving an activity."""
        mock_load_config.return_value = {"activities": {}}
        activity = ModelsActivity("test", 10, 20, 1.0, 0, 15, ("08:00", "18:00"))
        
        self.activity_service.save_activity(activity)
        
        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]
        self.assertIn("test", saved_config["activities"])
    
    @patch('cli_weather.core.activity_service.save_config')
    @patch('cli_weather.core.activity_service.load_config')
    def test_delete_activity(self, mock_load_config, mock_save_config):
        """Test deleting an activity."""
        mock_load_config.return_value = {"activities": self.sample_activities}
        
        result = self.activity_service.delete_activity("hiking")
        
        self.assertTrue(result)
        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]
        self.assertNotIn("hiking", saved_config["activities"])
    
    @patch('cli_weather.core.activity_service.load_config')
    def test_get_activity_names(self, mock_load_config):
        """Test getting list of activity names."""
        mock_config = {"activities": self.sample_activities}
        mock_load_config.return_value = mock_config
        
        names = self.activity_service.get_activity_names()
        
        self.assertEqual(names, ["hiking"])


class TestWeatherApp(unittest.TestCase):
    """Test the WeatherApp orchestrator class."""
    
    def setUp(self):
        """Set up test environment."""
        with patch('cli_weather.core.app.WeatherService'), \
             patch('cli_weather.core.app.LocationService'), \
             patch('cli_weather.core.app.ActivityService'), \
             patch('cli_weather.core.app.CacheManager'):
            self.weather_app = WeatherApp()
    
    def test_get_current_weather(self):
        """Test getting current weather through app."""
        # Mock the weather service
        mock_weather = WeatherData("2023-03-15 12:00:00", 20.0, "sunny", 10.0, 0)
        self.weather_app.weather_service.get_current_weather = Mock(return_value=mock_weather)
        
        location = ModelsLocation("Test", 40.0, -74.0)
        result = self.weather_app.get_current_weather(location)
        
        self.assertEqual(result, mock_weather)
        self.weather_app.weather_service.get_current_weather.assert_called_once_with(40.0, -74.0)
    
    def test_get_locations(self):
        """Test getting locations through app."""
        mock_locations = {"Test": ModelsLocation("Test", 40.0, -74.0)}
        self.weather_app.location_service.load_locations = Mock(return_value=mock_locations)
        
        result = self.weather_app.get_locations()
        
        self.assertEqual(result, mock_locations)
        self.weather_app.location_service.load_locations.assert_called_once_with(False)
    
    def test_save_location(self):
        """Test saving location through app."""
        location = ModelsLocation("Test", 40.0, -74.0)
        self.weather_app.location_service.save_location = Mock()
        
        self.weather_app.save_location(location)
        
        self.weather_app.location_service.save_location.assert_called_once_with(location)
    
    def test_get_activities(self):
        """Test getting activities through app."""
        mock_activities = {"test": Mock(spec=ModelsActivity)}
        self.weather_app.activity_service.load_activities = Mock(return_value=mock_activities)
        
        result = self.weather_app.get_activities()
        
        self.assertEqual(result, mock_activities)
        self.weather_app.activity_service.load_activities.assert_called_once()
    
    def test_clear_cache(self):
        """Test clearing cache through app."""
        self.weather_app.cache_manager.clear = Mock()
        
        self.weather_app.clear_cache()
        
        self.weather_app.cache_manager.clear.assert_called_once()


class TestModels(unittest.TestCase):
    """Test the data models."""
    
    def test_location_model(self):
        """Test Location model."""
        location = ModelsLocation("Test City", 40.7128, -74.0060)
        
        self.assertEqual(location.name, "Test City")
        self.assertEqual(location.latitude, 40.7128)
        self.assertEqual(location.longitude, -74.0060)
        
        coords = location.to_coordinates()
        self.assertEqual(coords, (40.7128, -74.0060))
    
    def test_location_from_coordinates(self):
        """Test creating Location from coordinate string."""
        location = ModelsLocation.from_coordinates("Test", "40.7128, -74.0060")
        
        self.assertEqual(location.name, "Test")
        self.assertEqual(location.latitude, 40.7128)
        self.assertEqual(location.longitude, -74.0060)
        
        # Test invalid format
        with self.assertRaises(ValueError):
            ModelsLocation.from_coordinates("Test", "invalid")
    
    def test_weather_data_model(self):
        """Test WeatherData model."""
        date_obj = datetime(2023, 3, 15, 12, 0, 0)
        weather = WeatherData("2023-03-15 12:00:00", 20.0, "sunny", 10.0, 0.5)
        
        self.assertEqual(weather.date, "2023-03-15 12:00:00")
        self.assertEqual(weather.temp, 20.0)
        self.assertEqual(weather.weather, "sunny")
        self.assertEqual(weather.wind_speed, 10.0)
        self.assertEqual(weather.rain, 0.5)
        
        data_dict = weather.to_dict()
        self.assertIn("date", data_dict)
        self.assertIn("temp", data_dict)
    
    def test_activity_model(self):
        """Test Activity model."""
        activity = ModelsActivity("hiking", 10, 25, 2.0, 5.0, 20.0, ("06:00", "18:00"))
        
        self.assertEqual(activity.name, "hiking")
        self.assertEqual(activity.temp_min, 10)
        self.assertEqual(activity.temp_max, 25)
        self.assertEqual(activity.max_rain, 2.0)
        self.assertEqual(activity.wind_min, 5.0)
        self.assertEqual(activity.wind_max, 20.0)
        self.assertEqual(activity.time_range, ("06:00", "18:00"))
        
        # Test to_dict method
        data_dict = activity.to_dict()
        self.assertEqual(data_dict["temp_min"], 10)
        self.assertEqual(data_dict["temp_max"], 25)
        
        # Test from_dict method
        activity2 = ModelsActivity.from_dict("test", data_dict)
        self.assertEqual(activity2.name, "test")
        self.assertEqual(activity2.temp_min, 10)


class TestCacheService(unittest.TestCase):
    """Test the cache service functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cache_expiry = timedelta(minutes=30)
        self.cache_manager = CacheManager(self.temp_dir, self.cache_expiry)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cache_save_and_load(self):
        """Test saving and loading cache data."""
        test_data = {"test": "data", "number": 42}
        key = "test_key"
        
        self.cache_manager.save(key, test_data)
        loaded_data = self.cache_manager.load(key)
        
        self.assertEqual(loaded_data, test_data)
    
    def test_cache_expiry(self):
        """Test cache expiry functionality."""
        test_data = {"test": "data"}
        key = "test_key"
        
        # Save with very short expiry
        short_expiry_cache = CacheManager(self.temp_dir, timedelta(microseconds=1))
        short_expiry_cache.save(key, test_data)
        
        # Wait for expiry
        import time
        time.sleep(0.001)
        
        loaded_data = short_expiry_cache.load(key)
        self.assertIsNone(loaded_data)  # Should be None due to expiry
    
    def test_cache_clear(self):
        """Test cache clearing."""
        test_data = {"test": "data"}
        key = "test_key"
        
        self.cache_manager.save(key, test_data)
        self.assertIsNotNone(self.cache_manager.load(key))
        
        self.cache_manager.clear()
        self.assertIsNone(self.cache_manager.load(key))


if __name__ == '__main__':
    unittest.main()
