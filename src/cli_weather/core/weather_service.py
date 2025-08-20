"""
Core weather service module.

This module contains the business logic for weather operations,
separated from any UI concerns.
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

import requests

from ..legacy.utils import CLIWeatherException, CacheManager
from ..legacy.config import API_KEY, LOCAL_TIMEZONE

logger = logging.getLogger(__name__)


class WeatherData:
    """Data class for weather information."""
    
    def __init__(self, date: str, temp: float, weather: str, wind_speed: float, rain: float):
        self.date = date
        self.temp = temp
        self.weather = weather
        self.wind_speed = wind_speed
        self.rain = rain
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for compatibility."""
        return {
            "date": self.date,
            "temp": self.temp,
            "weather": self.weather,
            "wind_speed": self.wind_speed,
            "rain": self.rain
        }


class WeatherService:
    """Core weather service for fetching and processing weather data."""
    
    def __init__(self, api_key: str, cache_manager: CacheManager):
        self.api_key = api_key
        self.cache_manager = cache_manager
    
    def fetch_weather_data(self, lat: float, lon: float, forecast_type: str = "5-day") -> Dict:
        """Fetches weather data from API or cache."""
        cache_key = self.cache_manager._generate_key(lat, lon, forecast_type)
        cached_data = self.cache_manager.load(cache_key)
        
        if cached_data:
            logger.debug(f"Using cached data for {forecast_type}")
            return cached_data
        
        urls = {
            "5-day": f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={self.api_key}&units=metric",
            "hourly": f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={self.api_key}&units=metric",
            "current": f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={self.api_key}&units=metric",
        }
        
        try:
            logger.debug(f"Fetching weather data for: '{forecast_type}' forecast")
            response = requests.get(urls[forecast_type], timeout=10)
            response.raise_for_status()
            logger.debug(f"Data for {forecast_type} fetched successfully.")
            
            data = response.json()
            self.cache_manager.save(cache_key, data)
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"Failed to fetch weather data. Location not found: {lat}, {lon}")
                raise CLIWeatherException("Failed to fetch weather data. Location not found!")
            elif e.response.status_code == 401:
                logger.error(f"Failed to fetch weather data. Invalid API key: {self.api_key}")
                raise CLIWeatherException(f"Failed to fetch weather data. Invalid API key: {self.api_key}")
            else:
                logger.error(f"Failed to fetch weather data, HTTP error occurred: {e.response.status_code} {e.response.reason}")
                raise CLIWeatherException(f"Failed to fetch weather data, {e.response.reason}.")
        except requests.exceptions.Timeout as e:
            logger.error(f"Error fetching weather data, connection timed out: {e}")
            raise CLIWeatherException("Request timed out, Please check your network connection.")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to fetch weather data, connection error: {e}")
            raise CLIWeatherException("Network error, Please check your connection and try again.")
        except requests.exceptions.RequestException as e:
            logger.exception(f"Error fetching weather data: {e}")
            raise CLIWeatherException("Failed to fetch weather data, Unexpected request error occurred.")
    
    def parse_current_weather(self, data: Dict) -> WeatherData:
        """Parse current weather data."""
        logger.debug("Parsing current weather data")
        local_time = datetime.fromtimestamp(data["dt"], tz=ZoneInfo(LOCAL_TIMEZONE))
        
        return WeatherData(
            date=local_time.strftime("%Y-%m-%d %H:%M:%S"),
            temp=data["main"]["temp"],
            weather=data["weather"][0]["description"],
            wind_speed=data["wind"]["speed"] * 3.6,
            rain=data.get("rain", {}).get("1h", 0)
        )
    
    def parse_hourly_weather(self, data: Dict, hours: int = 24) -> List[WeatherData]:
        """Parse hourly weather data."""
        logger.debug(f"Parsing hourly weather data for {hours} hours")
        hourly_weather = []
        
        for forecast in data["list"][:hours]:
            local_time = datetime.fromtimestamp(forecast["dt"], tz=ZoneInfo(LOCAL_TIMEZONE))
            hourly_weather.append(WeatherData(
                date=local_time.strftime("%Y-%m-%d %H:%M:%S"),
                temp=forecast["main"]["temp"],
                weather=forecast["weather"][0]["description"],
                wind_speed=forecast["wind"]["speed"] * 3.6,
                rain=forecast.get("rain", {}).get("3h", 0)
            ))
        
        logger.debug(f"Parsed hourly weather data successfully")
        return hourly_weather
    
    def parse_daily_weather(self, data: Dict) -> List[WeatherData]:
        """Parse daily weather data."""
        logger.debug("Parsing daily weather data")
        daily_weather = []
        
        for i in range(0, len(data["list"]), 8):  # 8 intervals = 1 day
            forecast = data["list"][i]
            local_time = datetime.fromtimestamp(forecast["dt"], tz=ZoneInfo(LOCAL_TIMEZONE))
            daily_weather.append(WeatherData(
                date=local_time.strftime("%Y-%m-%d"),
                temp=forecast["main"]["temp"],
                weather=forecast["weather"][0]["description"],
                wind_speed=forecast["wind"]["speed"] * 3.6,
                rain=forecast.get("rain", {}).get("3h", 0)
            ))
        
        logger.debug("Parsed daily weather data successfully")
        return daily_weather
    
    def get_current_weather(self, lat: float, lon: float) -> WeatherData:
        """Get current weather for location."""
        raw_data = self.fetch_weather_data(lat, lon, "current")
        return self.parse_current_weather(raw_data)
    
    def get_hourly_forecast(self, lat: float, lon: float, hours: int = 24) -> List[WeatherData]:
        """Get hourly forecast for location."""
        raw_data = self.fetch_weather_data(lat, lon, "hourly")
        return self.parse_hourly_weather(raw_data, hours)
    
    def get_daily_forecast(self, lat: float, lon: float) -> List[WeatherData]:
        """Get daily forecast for location."""
        raw_data = self.fetch_weather_data(lat, lon, "5-day")
        return self.parse_daily_weather(raw_data)
    
    def filter_best_days_for_activity(
        self, 
        daily_weather: List[WeatherData], 
        hourly_weather: List[WeatherData],
        activity_criteria: Dict
    ) -> List[WeatherData]:
        """Filter best days for specific activity based on criteria."""
        logger.debug("Filtering best weather days for activity...")
        
        time_range = activity_criteria.get("time_range", ["00:00", "23:59"])
        
        # Handle time-specific activities
        if time_range != ["00:00", "23:59"]:
            def is_within_time_range(weather_data: WeatherData) -> bool:
                time = datetime.strptime(weather_data.date.split(" ")[1], "%H:%M:%S").time()
                return (
                    datetime.strptime(time_range[0], "%H:%M").time()
                    <= time <=
                    datetime.strptime(time_range[1], "%H:%M").time()
                )
            
            hourly_within_range = [hour for hour in hourly_weather if is_within_time_range(hour)]
            daily_summary = defaultdict(list)
            
            for hour in hourly_within_range:
                date = hour.date.split(" ")[0]
                daily_summary[date].append(hour)
            
            best_days = []
            for date, hours in daily_summary.items():
                avg_temp = sum(h.temp for h in hours) / len(hours)
                total_rain = sum(h.rain for h in hours)
                max_wind = max(h.wind_speed for h in hours)
                min_wind = min(h.wind_speed for h in hours)
                avg_wind = sum(float(w) for w in [min_wind, max_wind]) / 2
                
                # Check criteria
                if (
                    activity_criteria["temp_min"] <= avg_temp <= activity_criteria["temp_max"]
                    and total_rain <= activity_criteria["rain"]
                    and activity_criteria.get("wind_min", 0) <= min_wind
                    and max_wind <= activity_criteria["wind_max"]
                ):
                    best_days.append(WeatherData(
                        date=date,
                        temp=avg_temp,
                        weather="N/A",  # Could aggregate weather descriptions
                        wind_speed=avg_wind,
                        rain=total_rain
                    ))
            
            logger.debug("Best days for activity filtered successfully.")
            return sorted(
                best_days,
                key=lambda x: (
                    abs((activity_criteria["temp_min"] + activity_criteria["temp_max"]) / 2 - x.temp),
                    x.rain,
                    x.wind_speed,
                ),
            )
        
        # Handle non-time-specific activities
        best_days = [
            day for day in daily_weather
            if (
                activity_criteria["temp_min"] <= day.temp <= activity_criteria["temp_max"]
                and day.rain <= activity_criteria["rain"]
                and activity_criteria.get("wind_min", 0) <= day.wind_speed
                and day.wind_speed <= activity_criteria["wind_max"]
            )
        ]
        
        logger.debug("Best days for activity filtered successfully.")
        return sorted(
            best_days,
            key=lambda x: (
                abs((activity_criteria["temp_min"] + activity_criteria["temp_max"]) / 2 - x.temp),
                x.rain,
                x.wind_speed,
            ),
        )[:5]
    
    def fetch_typhoon_data(self, lat: float, lon: float) -> Dict:
        """Fetch typhoon data and weather alerts."""
        try:
            url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,hourly,daily&appid={self.api_key}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            return {
                "alerts": data.get("alerts", []),
                "current": data.get("current", {}),
                "timezone": data.get("timezone", "UTC"),
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching typhoon data: {e}")
            raise CLIWeatherException(
                "Failed to fetch typhoon data. Please check your internet connection and API key."
            )
