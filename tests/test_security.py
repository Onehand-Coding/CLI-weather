from datetime import timedelta
from unittest.mock import MagicMock

import pytest
import requests

from cli_weather.core.weather_service import WeatherService
from cli_weather.legacy import weather as legacy_weather
from cli_weather.legacy.utils import CacheManager, CLIWeatherException


def _http_error(status_code):
    response = MagicMock()
    response.status_code = status_code
    response.reason = "Unauthorized"
    response.raise_for_status.side_effect = requests.HTTPError(response=response)
    return response


def test_core_401_does_not_log_api_key(monkeypatch, caplog):
    cache = MagicMock()
    cache.load.return_value = None
    cache._generate_key.return_value = "key"
    service = WeatherService("super-secret", cache)
    monkeypatch.setattr(
        "cli_weather.core.weather_service.requests.get",
        lambda *args, **kwargs: _http_error(401),
    )

    with pytest.raises(CLIWeatherException) as exc:
        service.fetch_weather_data(1.0, 2.0, "current")

    assert "super-secret" not in str(exc.value)
    assert "super-secret" not in caplog.text


def test_legacy_401_does_not_log_api_key(tmp_path, monkeypatch, caplog):
    cache = CacheManager(tmp_path, timedelta(minutes=1))
    monkeypatch.setattr(
        legacy_weather.requests,
        "get",
        lambda *args, **kwargs: _http_error(401),
    )

    with pytest.raises(CLIWeatherException) as exc:
        legacy_weather.fetch_weather_data(1.0, 2.0, "super-secret", cache)

    assert "super-secret" not in str(exc.value)
    assert "super-secret" not in caplog.text
