"""Custom exceptions for the CLI Weather application."""


class WeatherAppError(Exception):
    """Base exception for CLI Weather application."""
    
    def __init__(self, message: str, cause: Exception = None):
        super().__init__(message)
        self.cause = cause


class WeatherAPIError(WeatherAppError):
    """Exception raised when weather API requests fail."""
    pass


class LocationError(WeatherAppError):
    """Exception raised for location-related errors."""
    pass


class ActivityError(WeatherAppError):
    """Exception raised for activity-related errors."""
    pass


class ConfigError(WeatherAppError):
    """Exception raised for configuration-related errors."""
    pass


class CacheError(WeatherAppError):
    """Exception raised for cache-related errors."""
    pass
