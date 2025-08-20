"""Data models for the CLI Weather application."""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from datetime import datetime


@dataclass
class Location:
    """Represents a geographic location."""
    
    name: str
    latitude: float
    longitude: float
    
    def to_coordinates(self) -> Tuple[float, float]:
        """Return location as (lat, lon) tuple."""
        return (self.latitude, self.longitude)
    
    def to_coord_string(self) -> str:
        """Return location as coordinate string 'lat, lon'."""
        return f"{self.latitude}, {self.longitude}"
    
    @classmethod
    def from_coordinates(cls, name: str, coordinates: str) -> "Location":
        """Create Location from coordinate string 'lat, lon'."""
        try:
            lat_str, lon_str = coordinates.split(",")
            return cls(
                name=name,
                latitude=float(lat_str.strip()),
                longitude=float(lon_str.strip())
            )
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid coordinate format: {coordinates}") from e


@dataclass
class WeatherData:
    """Represents weather data for a specific time."""
    
    date: datetime
    temperature: float  # Celsius
    weather_description: str
    wind_speed: float  # km/h
    rain: float  # mm
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "date": self.date.strftime("%Y-%m-%d %H:%M:%S"),
            "temp": self.temperature,
            "weather": self.weather_description,
            "wind_speed": self.wind_speed,
            "rain": self.rain
        }


@dataclass
class Activity:
    """Represents an activity with weather criteria."""
    
    name: str
    temp_min: int  # °C
    temp_max: int  # °C
    max_rain: float  # mm
    wind_min: float  # km/h
    wind_max: float  # km/h
    time_range: Tuple[str, str]  # (start_time, end_time) in "HH:MM" format
    
    def matches_weather(self, weather: WeatherData, check_time: bool = True) -> bool:
        """Check if weather conditions match activity criteria."""
        # Check temperature
        if not (self.temp_min <= weather.temperature <= self.temp_max):
            return False
            
        # Check rain
        if weather.rain > self.max_rain:
            return False
            
        # Check wind
        if not (self.wind_min <= weather.wind_speed <= self.wind_max):
            return False
            
        # Check time range if specified
        if check_time and self.time_range != ("00:00", "23:59"):
            weather_time = weather.date.time()
            start_time = datetime.strptime(self.time_range[0], "%H:%M").time()
            end_time = datetime.strptime(self.time_range[1], "%H:%M").time()
            
            if not (start_time <= weather_time <= end_time):
                return False
                
        return True
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "temp_min": self.temp_min,
            "temp_max": self.temp_max,
            "rain": self.max_rain,
            "wind_min": self.wind_min,
            "wind_max": self.wind_max,
            "time_range": list(self.time_range)
        }
    
    @classmethod
    def from_dict(cls, name: str, data: Dict) -> "Activity":
        """Create Activity from dictionary."""
        return cls(
            name=name,
            temp_min=data["temp_min"],
            temp_max=data["temp_max"],
            max_rain=data["rain"],
            wind_min=data.get("wind_min", 0),
            wind_max=data["wind_max"],
            time_range=(data["time_range"][0], data["time_range"][1])
        )


@dataclass
class WeatherAlert:
    """Represents a weather alert or typhoon warning."""
    
    event: str
    severity: str
    start_time: str
    end_time: str
    description: str
    
    @classmethod
    def from_dict(cls, data: Dict) -> "WeatherAlert":
        """Create WeatherAlert from API response dictionary."""
        return cls(
            event=data["event"],
            severity=data["severity"],
            start_time=data["start"],
            end_time=data["end"],
            description=data["description"]
        )
