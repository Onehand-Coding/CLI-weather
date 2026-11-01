import json

from cli_weather.core.app import WeatherApp
from cli_weather.core.config_service import ConfigService
from cli_weather.core.models import Activity, Location
from cli_weather.core.weather_service import WeatherService
from cli_weather.legacy.utils import CacheManager


def test_weather_service_timezone():
    service = WeatherService("key", CacheManager.__new__(CacheManager), "Asia/Manila")
    assert service.tz.key == "Asia/Manila"


def test_weather_app_uses_custom_config(tmp_path):
    config = ConfigService(tmp_path)
    app = WeatherApp(config)

    app.save_location(Location("Home", 1.0, 2.0))
    app.save_activity(Activity("walk", 10, 20, 1.0, 0, 10.0, ("06:00", "18:00")))

    data = json.loads(config.config_file.read_text())
    assert "Home" in data["locations"]
    assert "walk" in data["activities"]
