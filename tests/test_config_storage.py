import json
import os
import stat

from cli_weather.core.config_service import ConfigService


def test_default_config_file_under_custom_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CLI_WEATHER_CONFIG_DIR", str(tmp_path))
    service = ConfigService()
    assert service.config_file == tmp_path / "config.json"
    assert service.api_key == ""
    assert service.timezone == "UTC"
    assert service.log_level == "ERROR"


def test_save_and_load_api_key(tmp_path):
    service = ConfigService(tmp_path)
    service.save_config({"api_key": "secret", "timezone": "Asia/Manila"})

    assert service.api_key == "secret"
    assert service.timezone == "Asia/Manila"
    assert json.loads(service.config_file.read_text())["api_key"] == "secret"


def test_config_permissions(tmp_path):
    service = ConfigService(tmp_path)
    service.save_config({"api_key": "secret"})
    if os.name == "posix":
        assert stat.S_IMODE(service.config_file.stat().st_mode) == 0o600


def test_missing_file_returns_defaults(tmp_path):
    service = ConfigService(tmp_path)
    config = service.load_config()
    assert config["api_key"] == ""
    assert "locations" in config
    assert not service.config_file.exists()


def test_invalid_json_returns_defaults(tmp_path):
    service = ConfigService(tmp_path)
    service.config_file.write_text("{invalid")
    assert service.load_config()["api_key"] == ""


def test_env_api_key_override(tmp_path, monkeypatch):
    monkeypatch.setenv("OWM_API_KEY", "from-env")
    service = ConfigService(tmp_path)
    assert service.api_key == "from-env"


def test_locations_and_activities_round_trip(tmp_path):
    from cli_weather.core.models import Activity, Location

    service = ConfigService(tmp_path)
    service.save_location(Location("Home", 1.0, 2.0))
    service.save_activity(Activity("walk", 10, 20, 1.0, 0, 10.0, ("06:00", "18:00")))

    assert service.get_locations()["Home"].latitude == 1.0
    assert service.get_activities()["walk"].temp_max == 20
