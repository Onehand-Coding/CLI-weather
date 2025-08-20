"""
Core application orchestrator.

This module provides the main application class that orchestrates
all core services and provides a unified interface for the UI layers.
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from .weather_service import WeatherService, WeatherData
from .location_service import LocationService, Location
from .activity_service import ActivityService, Activity
from ..legacy.utils import CLIWeatherException, CacheManager
from ..legacy.config import API_KEY, CACHED_DIR, CACHE_EXPIRY, LOG_DIR

logger = logging.getLogger(__name__)


class WeatherApp:
    """Core application class that orchestrates all services."""
    
    def __init__(self):
        """Initialize the weather application."""
        self.cache_manager = CacheManager(CACHED_DIR, CACHE_EXPIRY)
        self.weather_service = WeatherService(API_KEY, self.cache_manager)
        self.location_service = LocationService()
        self.activity_service = ActivityService()
    
    # Weather-related methods
    def get_current_weather(self, location: Location) -> WeatherData:
        """Get current weather for a location."""
        return self.weather_service.get_current_weather(location.latitude, location.longitude)
    
    def get_hourly_forecast(self, location: Location, hours: int = 24) -> List[WeatherData]:
        """Get hourly forecast for a location."""
        return self.weather_service.get_hourly_forecast(location.latitude, location.longitude, hours)
    
    def get_daily_forecast(self, location: Location) -> List[WeatherData]:
        """Get daily forecast for a location."""
        return self.weather_service.get_daily_forecast(location.latitude, location.longitude)
    
    def get_specific_day_forecast(self, location: Location, day_index: int) -> Tuple[WeatherData, List[WeatherData]]:
        """Get forecast for a specific day including hourly details."""
        daily_forecast = self.get_daily_forecast(location)
        if day_index < 0 or day_index >= len(daily_forecast):
            raise CLIWeatherException("Invalid day index")
        
        selected_day = daily_forecast[day_index]
        hourly_forecast = self.get_hourly_forecast(location)
        
        # Filter hourly forecast for the selected day
        selected_date = selected_day.date
        day_hourly = [
            hour for hour in hourly_forecast 
            if hour.date.startswith(selected_date)
        ]
        
        return selected_day, day_hourly
    
    def get_best_activity_days(self, location: Location, activity_name: str) -> List[WeatherData]:
        """Get best days for an activity at a location."""
        activity = self.activity_service.get_activity(activity_name)
        if not activity:
            raise CLIWeatherException(f"Activity '{activity_name}' not found")
        
        daily_forecast = self.get_daily_forecast(location)
        hourly_forecast = self.get_hourly_forecast(location)
        
        return self.weather_service.filter_best_days_for_activity(
            daily_forecast, 
            hourly_forecast, 
            activity.to_dict()
        )
    
    def get_typhoon_alerts(self, location: Location) -> Dict:
        """Get typhoon alerts for a location."""
        return self.weather_service.fetch_typhoon_data(location.latitude, location.longitude)
    
    # Location-related methods
    def get_locations(self, include_sensitive: bool = False) -> Dict[str, Location]:
        """Get all saved locations."""
        return self.location_service.load_locations(include_sensitive)
    
    def save_location(self, location: Location) -> None:
        """Save a location."""
        self.location_service.save_location(location)
    
    def delete_location(self, location_name: str) -> bool:
        """Delete a location."""
        return self.location_service.delete_location(location_name)
    
    def get_current_location(self) -> Location:
        """Get current location using IP geolocation."""
        return self.location_service.get_current_location()
    
    def search_locations(self, query: str) -> List[Location]:
        """Search for locations."""
        return self.location_service.search_locations(query)
    
    def geocode_address(self, address: str) -> Location:
        """Geocode an address to get location."""
        return self.location_service.geocode_address(address)
    
    def create_location_from_coordinates(self, name: str, lat: float, lon: float) -> Location:
        """Create a location from coordinates."""
        if not self.location_service.validate_coordinates(lat, lon):
            raise CLIWeatherException("Invalid coordinates")
        return Location(name, lat, lon)
    
    # Activity-related methods
    def get_activities(self) -> Dict[str, Activity]:
        """Get all saved activities."""
        return self.activity_service.load_activities()
    
    def get_activity(self, name: str) -> Optional[Activity]:
        """Get a specific activity."""
        return self.activity_service.get_activity(name)
    
    def save_activity(self, activity: Activity) -> None:
        """Save an activity."""
        self.activity_service.save_activity(activity)
    
    def delete_activity(self, activity_name: str) -> bool:
        """Delete an activity."""
        return self.activity_service.delete_activity(activity_name)
    
    def create_activity(
        self, 
        name: str, 
        temp_min: int, 
        temp_max: int, 
        rain: float, 
        wind_max: float,
        wind_min: float = 0,
        time_range: Optional[List[str]] = None
    ) -> Activity:
        """Create a new activity."""
        return self.activity_service.create_activity(
            name, temp_min, temp_max, rain, wind_max, wind_min, time_range
        )
    
    def get_activity_names(self) -> List[str]:
        """Get list of activity names."""
        return self.activity_service.get_activity_names()
    
    # Utility methods
    def clear_cache(self) -> None:
        """Clear weather data cache."""
        self.cache_manager.clear()
    
    def clear_logs(self) -> None:
        """Clear application logs."""
        for file in LOG_DIR.iterdir():
            if file.is_file():
                file.unlink()
        logger.debug("Cleared logs successfully.")
    
    def save_weather_to_file(
        self, 
        location: Location, 
        weather_data: List[WeatherData], 
        file_path: Path,
        activity_name: Optional[str] = None
    ) -> None:
        """Save weather forecast to a file."""
        logger.debug(f"Saving weather forecast for {location.name}...")
        
        filename = f"{location.name}_{activity_name}_weather.txt" if activity_name else f"{location.name}_weather.txt"
        forecast_file = file_path / filename
        
        with open(forecast_file, "w") as file:
            header = f"\nBest {activity_name.title()} Days:\n" if activity_name else "Weather Forecast:\n"
            file.write(header)
            for weather in weather_data:
                file.write(
                    f"Date: {weather.date}, Temp: {weather.temp:.2f}°C, Weather: {weather.weather.title()}, "
                    f"Wind: {weather.wind_speed:.2f} km/h, Rain: {weather.rain} mm\n"
                )
        
        logger.debug(f"Weather forecast saved to '{forecast_file}'")
    
    def save_typhoon_alerts_to_file(self, location: Location, alerts_data: Dict, file_path: Path) -> None:
        """Save typhoon alerts to a file."""
        filename = f"typhoon_alerts_{location.name.replace(' ', '_')}_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        alerts_file = file_path / filename
        
        try:
            with open(alerts_file, "w", encoding="utf-8") as f:
                f.write(f"Weather Alerts for {location.name}\n")
                f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                if alerts_data.get("alerts"):
                    for alert in alerts_data["alerts"]:
                        f.write("=" * 50 + "\n")
                        f.write(f"Alert: {alert['event']}\n")
                        f.write(f"Severity: {alert['severity'].upper()}\n")
                        f.write(f"Start: {alert['start']}\n")
                        f.write(f"End: {alert['end']}\n")
                        f.write(f"Description: {alert['description']}\n")
                        f.write("=" * 50 + "\n")
                else:
                    f.write("No active weather alerts or typhoons in this area.\n")
            
            logger.debug(f"Alerts saved to {alerts_file}")
        except Exception as e:
            logger.error(f"Error saving alerts to file: {e}")
            raise CLIWeatherException("Error saving alerts to file.")
