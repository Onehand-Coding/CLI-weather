"""
Core activity service module.

This module contains the business logic for activity management operations,
separated from any UI concerns.
"""

import logging
from typing import Dict, List, Optional

from ..legacy.config import load_config, save_config
from ..legacy.utils import CLIWeatherException

logger = logging.getLogger(__name__)


class Activity:
    """Data class for activity information."""
    
    def __init__(
        self, 
        name: str, 
        temp_min: int, 
        temp_max: int, 
        rain: float, 
        wind_max: float,
        wind_min: float = 0,
        time_range: Optional[List[str]] = None
    ):
        self.name = name
        self.temp_min = temp_min
        self.temp_max = temp_max
        self.rain = rain
        self.wind_max = wind_max
        self.wind_min = wind_min
        self.time_range = time_range or ["00:00", "23:59"]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "temp_min": self.temp_min,
            "temp_max": self.temp_max,
            "rain": self.rain,
            "wind_min": self.wind_min,
            "wind_max": self.wind_max,
            "time_range": self.time_range
        }
    
    @classmethod
    def from_dict(cls, name: str, data: Dict) -> 'Activity':
        """Create Activity from dictionary data."""
        return cls(
            name=name,
            temp_min=data["temp_min"],
            temp_max=data["temp_max"],
            rain=data["rain"],
            wind_max=data["wind_max"],
            wind_min=data.get("wind_min", 0),
            time_range=data.get("time_range", ["00:00", "23:59"])
        )
    
    def is_time_specific(self) -> bool:
        """Check if activity has specific time requirements."""
        return self.time_range != ["00:00", "23:59"]
    
    def get_formatted_criteria(self) -> Dict[str, str]:
        """Get formatted criteria for display."""
        return {
            "Temperature Range": f"{self.temp_min}-{self.temp_max} °C",
            "Max Rain": f"{self.rain} mm",
            "Wind Range": f"{self.wind_min}-{self.wind_max} km/h",
            "Time Range": f"{self.time_range[0]} to {self.time_range[1]}" if self.is_time_specific() else "All Day"
        }


class ActivityService:
    """Core activity service for managing weather activities."""
    
    def load_activities(self) -> Dict[str, Activity]:
        """Load all saved activities."""
        logger.debug("Loading activities...")
        config = load_config()
        activities = {}
        
        for name, criteria in config.get("activities", {}).items():
            try:
                activities[name] = Activity.from_dict(name, criteria)
            except (KeyError, TypeError) as e:
                logger.warning(f"Skipping invalid activity '{name}': {e}")
        
        logger.debug(f"Loaded {len(activities)} activities successfully.")
        return activities
    
    def get_activity(self, name: str) -> Optional[Activity]:
        """Get a specific activity by name."""
        activities = self.load_activities()
        return activities.get(name)
    
    def save_activity(self, activity: Activity) -> None:
        """Save an activity to the configuration file."""
        logger.debug(f"Saving activity: {activity.name}")
        configuration = load_config()
        configuration.setdefault("activities", {})[activity.name] = activity.to_dict()
        save_config(configuration)
        logger.debug(f"'{activity.name}' saved successfully.")
    
    def delete_activity(self, activity_name: str) -> bool:
        """Delete an activity from saved activities."""
        try:
            config = load_config()
            activities = config.get("activities", {})
            
            if activity_name in activities:
                del config["activities"][activity_name]
                save_config(config)
                logger.debug(f"Activity '{activity_name}' deleted successfully.")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting activity '{activity_name}': {e}")
            raise CLIWeatherException(f"Error deleting activity: {e}")
    
    def validate_activity_criteria(self, criteria: Dict) -> bool:
        """Validate activity criteria values."""
        try:
            # Check required fields
            required_fields = ["temp_min", "temp_max", "rain", "wind_max"]
            for field in required_fields:
                if field not in criteria:
                    return False
            
            # Check value ranges
            if criteria["temp_min"] >= criteria["temp_max"]:
                return False
            
            if criteria["rain"] < 0 or criteria["wind_max"] < 0:
                return False
            
            if "wind_min" in criteria and criteria["wind_min"] > criteria["wind_max"]:
                return False
            
            # Validate time range if present
            if "time_range" in criteria and criteria["time_range"]:
                time_range = criteria["time_range"]
                if len(time_range) != 2:
                    return False
                # Could add more time format validation here
            
            return True
        except (TypeError, KeyError):
            return False
    
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
        """Create a new activity with validation."""
        if not name or not name.strip():
            raise CLIWeatherException("Activity name cannot be empty")
        
        activity = Activity(
            name=name.lower().strip(),
            temp_min=temp_min,
            temp_max=temp_max,
            rain=rain,
            wind_max=wind_max,
            wind_min=wind_min,
            time_range=time_range
        )
        
        if not self.validate_activity_criteria(activity.to_dict()):
            raise CLIWeatherException("Invalid activity criteria")
        
        return activity
    
    def get_activity_names(self) -> List[str]:
        """Get list of all activity names."""
        return list(self.load_activities().keys())
    
    def activity_exists(self, name: str) -> bool:
        """Check if an activity exists."""
        return name in self.load_activities()
    
    def update_activity(self, name: str, new_criteria: Dict) -> bool:
        """Update an existing activity."""
        if not self.activity_exists(name):
            return False
        
        if not self.validate_activity_criteria(new_criteria):
            raise CLIWeatherException("Invalid activity criteria")
        
        activity = Activity.from_dict(name, new_criteria)
        self.save_activity(activity)
        return True
