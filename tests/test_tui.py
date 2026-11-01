import asyncio

from textual.widgets import Input

from cli_weather.core.config_service import ConfigService
from cli_weather.ui.tui import (
    MainScreen,
    SettingsScreen,
    SetupScreen,
    WeatherTUI,
)


def test_setup_screen_without_api_key(tmp_path):
    config = ConfigService(tmp_path)

    async def scenario():
        app = WeatherTUI(config)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, SetupScreen)

    asyncio.run(scenario())


def test_main_screen_with_api_key(tmp_path):
    config = ConfigService(tmp_path)
    config.save_config({"api_key": "key"})

    async def scenario():
        app = WeatherTUI(config)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, MainScreen)

    asyncio.run(scenario())


def test_settings_save_updates_config(tmp_path):
    config = ConfigService(tmp_path)
    config.save_config({"api_key": "old"})

    async def scenario():
        app = WeatherTUI(config)
        async with app.run_test() as pilot:
            app.push_screen(SettingsScreen())
            await pilot.pause()
            app.screen.query_one("#api-key", Input).value = "new"
            app.screen.query_one("#timezone", Input).value = "Asia/Manila"
            await pilot.click("#save")
            await pilot.pause()

    asyncio.run(scenario())

    assert ConfigService(tmp_path).api_key == "new"
    assert ConfigService(tmp_path).timezone == "Asia/Manila"


def test_weather_screen_loads_current_weather(tmp_path):
    from unittest.mock import MagicMock

    from textual.widgets import DataTable

    from cli_weather.core.location_service import Location
    from cli_weather.core.weather_service import WeatherData
    from cli_weather.ui.tui import WeatherScreen

    config = ConfigService(tmp_path)
    config.save_config({"api_key": "key"})
    fake_app = MagicMock()
    fake_app.get_locations.return_value = {}
    fake_app.get_current_location.return_value = Location("Here", 1.0, 2.0)
    fake_app.get_current_weather.return_value = WeatherData(
        "2023-01-01", 20.0, "sunny", 5.0, 0.0
    )

    async def scenario():
        app = WeatherTUI(config)
        async with app.run_test() as pilot:
            app.weather_app = fake_app
            app.push_screen(WeatherScreen())
            await pilot.pause()
            await pilot.click("#load")
            await pilot.pause(0.5)
            table = app.screen.query_one("#weather-table", DataTable)
            assert table.row_count == 1
            fake_app.get_current_weather.assert_called_once()

    asyncio.run(scenario())
