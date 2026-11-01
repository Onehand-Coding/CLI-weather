"""Textual TUI for CLI Weather."""

from __future__ import annotations

import os

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Select,
    Static,
)

from ..core.config_service import ConfigService
from ..core.weather_service import WeatherData
from ..legacy.utils import CLIWeatherException

FORECAST_OPTIONS = [
    ("Current weather", "current"),
    ("Hourly (24h)", "hourly"),
    ("5-day forecast", "daily"),
    ("Specific day", "day"),
    ("Best activity day", "activity"),
    ("Typhoon alerts", "typhoon"),
]

CSS = """
Screen {
    layout: vertical;
}
#main-menu, #setup-form, #settings-form, #locations-form,
#activities-form, #weather-form {
    width: 90;
    height: auto;
    margin: 1 2;
}
.title {
    text-style: bold;
    margin-bottom: 1;
}
Button {
    width: 100%;
    margin: 1 0;
}
#weather-table, #weather-log {
    height: 1fr;
    margin: 1 2;
}
#status {
    margin-bottom: 1;
}
"""


def _save_settings(
    app: WeatherTUI,
    api_key: str,
    timezone: str,
    log_level: str,
) -> None:
    config = app.config.load_config()
    config.update(
        {
            "api_key": api_key.strip(),
            "timezone": timezone.strip() or "UTC",
            "log_level": log_level.strip().upper() or "ERROR",
        }
    )
    app.config.save_config(config)
    app.config.setup_logging()
    app.rebuild_weather_app()


class SetupScreen(Screen):
    """First-run setup for the API key and preferences."""

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="setup-form"):
            yield Static("Welcome to CLI Weather", classes="title")
            yield Static(
                "Enter an OpenWeatherMap API key. It is stored in your config file."
            )
            yield Label("API key")
            yield Input(password=True, id="api-key")
            yield Label("Timezone")
            yield Input(value=self.app.config.timezone, id="timezone")
            yield Label("Log level")
            yield Input(value=self.app.config.log_level, id="log-level")
            yield Button("Save", id="save", variant="primary")
            yield Button("Quit", id="quit")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
            return
        api_key = self.query_one("#api-key", Input).value.strip()
        if not api_key:
            self.notify("API key is required.", severity="error")
            return
        try:
            _save_settings(
                self.app,
                api_key,
                self.query_one("#timezone", Input).value,
                self.query_one("#log-level", Input).value,
            )
        except CLIWeatherException as exc:
            self.notify(str(exc), severity="error")
            return
        self.app.switch_screen(MainScreen())
        self.notify("Settings saved.")


class MainScreen(Screen):
    """Main TUI menu."""

    BINDINGS = [("s", "settings", "Settings")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main-menu"):
            yield Static("CLI Weather", classes="title")
            yield Static(self._status(), id="status")
            yield Button("Weather", id="weather")
            yield Button("Locations", id="locations")
            yield Button("Activities", id="activities")
            yield Button("Settings", id="settings")
            yield Button("Quit", id="quit")
        yield Footer()

    def _status(self) -> str:
        return (
            "API key configured."
            if self.app.config.api_key
            else "API key missing. Open Settings."
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "weather":
            self.app.push_screen(WeatherScreen())
        elif button_id == "locations":
            self.app.push_screen(LocationsScreen())
        elif button_id == "activities":
            self.app.push_screen(ActivitiesScreen())
        elif button_id == "settings":
            self.app.push_screen(SettingsScreen())
        elif button_id == "quit":
            self.app.exit()

    def action_settings(self) -> None:
        self.app.push_screen(SettingsScreen())


class WeatherScreen(Screen):
    """Fetch and display weather data."""

    BINDINGS = [("escape", "back", "Back")]

    def compose(self) -> ComposeResult:
        locations = self.app.weather_app.get_locations()
        location_options = [
            ("Current location", "__current__"),
            *[(name, name) for name in sorted(locations)],
            ("Manual coordinates", "__manual__"),
        ]
        yield Header()
        with Vertical(id="weather-form"):
            yield Static("Weather", classes="title")
            yield Select(
                FORECAST_OPTIONS,
                value="current",
                id="forecast",
                allow_blank=False,
            )
            yield Select(
                location_options,
                value="__current__",
                id="location",
                allow_blank=False,
            )
            yield Input(placeholder="Day 1-5 (specific day)", id="day")
            yield Input(
                placeholder="Activity name (best activity day)",
                id="activity",
            )
            yield Input(placeholder="Manual latitude", id="lat")
            yield Input(placeholder="Manual longitude", id="lon")
            yield Button("Load", id="load", variant="primary")
            yield Button("Back", id="back")
        yield DataTable(id="weather-table")
        yield RichLog(id="weather-log")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#weather-table", DataTable)
        table.add_columns("Date", "Temp", "Weather", "Wind", "Rain")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "load":
            self.load_weather()

    def action_back(self) -> None:
        self.app.pop_screen()

    def load_weather(self) -> None:
        forecast = self.query_one("#forecast", Select).value
        location_value = self.query_one("#location", Select).value
        day = self.query_one("#day", Input).value
        activity = self.query_one("#activity", Input).value
        lat = self.query_one("#lat", Input).value
        lon = self.query_one("#lon", Input).value
        self.notify("Loading weather...")
        self.fetch_weather(str(forecast), str(location_value), day, activity, lat, lon)

    @work(thread=True, exclusive=True)
    def fetch_weather(
        self,
        forecast: str,
        location_value: str,
        day: str,
        activity: str,
        lat: str,
        lon: str,
    ) -> None:
        try:
            app = self.app.weather_app
            if location_value == "__current__":
                location = app.get_current_location()
            elif location_value == "__manual__":
                location = app.create_location_from_coordinates(
                    "Manual", float(lat), float(lon)
                )
            else:
                location = app.get_locations().get(location_value)
                if location is None:
                    raise CLIWeatherException("Location not found.")

            if forecast == "current":
                rows = [app.get_current_weather(location)]
            elif forecast == "hourly":
                rows = app.get_hourly_forecast(location)
            elif forecast == "daily":
                rows = app.get_daily_forecast(location)
            elif forecast == "day":
                selected, hourly = app.get_specific_day_forecast(location, int(day) - 1)
                rows = [selected, *hourly]
            elif forecast == "activity":
                if not activity.strip():
                    raise CLIWeatherException("Enter an activity name.")
                rows = app.get_best_activity_days(location, activity.strip())
            elif forecast == "typhoon":
                data = app.get_typhoon_alerts(location)
                self.app.call_from_thread(self.show_typhoon, location.name, data)
                return
            else:
                raise CLIWeatherException("Unknown forecast type.")

            self.app.call_from_thread(self.show_rows, rows)
        except Exception as exc:
            self.app.call_from_thread(self.notify, str(exc), severity="error")

    def show_rows(self, rows: list[WeatherData]) -> None:
        table = self.query_one("#weather-table", DataTable)
        log = self.query_one("#weather-log", RichLog)
        log.clear()
        table.clear(columns=False)
        if not rows:
            self.notify("No matching forecast data.")
            return
        for weather in rows:
            table.add_row(
                weather.date,
                f"{weather.temp:.1f} C",
                weather.weather.title(),
                f"{weather.wind_speed:.1f} km/h",
                f"{weather.rain} mm",
            )
        self.notify(f"Loaded {len(rows)} row(s).")

    def show_typhoon(self, location_name: str, data: dict) -> None:
        log = self.query_one("#weather-log", RichLog)
        log.clear()
        alerts = data.get("alerts", []) if isinstance(data, dict) else []
        if not alerts:
            log.write(f"No active alerts for {location_name}.")
            return
        for alert in alerts:
            log.write(
                f"{alert.get('event', 'Alert')} "
                f"[{alert.get('severity', 'unknown')}]: "
                f"{alert.get('description', '')}"
            )


class LocationsScreen(Screen):
    """List and manage saved locations."""

    BINDINGS = [("escape", "back", "Back")]

    def __init__(self) -> None:
        super().__init__()
        self._names: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="locations-table")
        with Vertical(id="locations-form"):
            yield Static("Locations", classes="title")
            yield Input(placeholder="Name", id="loc-name")
            yield Input(placeholder="Address", id="loc-address")
            yield Input(placeholder="Latitude", id="loc-lat")
            yield Input(placeholder="Longitude", id="loc-lon")
            yield Button("Add by address", id="add-address")
            yield Button("Add by coordinates", id="add-coords")
            yield Button("Delete selected", id="delete")
            yield Button("Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#locations-table", DataTable)
        table.add_columns("Name", "Latitude", "Longitude")
        self.refresh_rows()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "add-address":
            self.add_by_address()
        elif event.button.id == "add-coords":
            self.add_by_coordinates()
        elif event.button.id == "delete":
            self.delete_selected()

    def action_back(self) -> None:
        self.app.pop_screen()

    def refresh_rows(self) -> None:
        table = self.query_one("#locations-table", DataTable)
        table.clear(columns=False)
        locations = self.app.weather_app.get_locations()
        self._names = sorted(locations)
        for name in self._names:
            location = locations[name]
            table.add_row(
                name,
                f"{location.latitude:.6f}",
                f"{location.longitude:.6f}",
            )

    def add_by_address(self) -> None:
        name = self.query_one("#loc-name", Input).value.strip()
        address = self.query_one("#loc-address", Input).value.strip()
        if not name or not address:
            self.notify("Name and address are required.", severity="error")
            return
        self.fetch_address(name, address)

    @work(thread=True, exclusive=True)
    def fetch_address(self, name: str, address: str) -> None:
        try:
            location = self.app.weather_app.geocode_address(address)
            location.name = name
            self.app.weather_app.save_location(location)
            self.app.call_from_thread(self.after_save, name)
        except Exception as exc:
            self.app.call_from_thread(self.notify, str(exc), severity="error")

    def add_by_coordinates(self) -> None:
        name = self.query_one("#loc-name", Input).value.strip()
        lat = self.query_one("#loc-lat", Input).value.strip()
        lon = self.query_one("#loc-lon", Input).value.strip()
        if not name or not lat or not lon:
            self.notify(
                "Name, latitude, and longitude are required.",
                severity="error",
            )
            return
        try:
            location = self.app.weather_app.create_location_from_coordinates(
                name, float(lat), float(lon)
            )
            self.app.weather_app.save_location(location)
        except Exception as exc:
            self.notify(str(exc), severity="error")
            return
        self.after_save(name)

    def after_save(self, name: str) -> None:
        self.refresh_rows()
        self.notify(f"Saved {name}.")

    def delete_selected(self) -> None:
        table = self.query_one("#locations-table", DataTable)
        row = table.cursor_row
        if row < 0 or row >= len(self._names):
            self.notify("Select a location to delete.", severity="error")
            return
        name = self._names[row]
        self.app.weather_app.delete_location(name)
        self.refresh_rows()
        self.notify(f"Deleted {name}.")


class ActivitiesScreen(Screen):
    """List and manage activity criteria."""

    BINDINGS = [("escape", "back", "Back")]

    def __init__(self) -> None:
        super().__init__()
        self._names: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="activities-table")
        with Vertical(id="activities-form"):
            yield Static("Activities", classes="title")
            yield Input(placeholder="Name", id="act-name")
            yield Input(placeholder="Temp min (C)", id="act-tmin")
            yield Input(placeholder="Temp max (C)", id="act-tmax")
            yield Input(placeholder="Max rain (mm)", id="act-rain")
            yield Input(placeholder="Wind min (km/h)", id="act-wmin")
            yield Input(placeholder="Wind max (km/h)", id="act-wmax")
            yield Input(placeholder="Start HH:MM", id="act-start")
            yield Input(placeholder="End HH:MM", id="act-end")
            yield Button("Add activity", id="add")
            yield Button("Delete selected", id="delete")
            yield Button("Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#activities-table", DataTable)
        table.add_columns("Name", "Temp", "Rain", "Wind", "Time")
        self.refresh_rows()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "add":
            self.add_activity()
        elif event.button.id == "delete":
            self.delete_selected()

    def action_back(self) -> None:
        self.app.pop_screen()

    def refresh_rows(self) -> None:
        table = self.query_one("#activities-table", DataTable)
        table.clear(columns=False)
        activities = self.app.weather_app.get_activities()
        self._names = sorted(activities)
        for name in self._names:
            activity = activities[name]
            table.add_row(
                name,
                f"{activity.temp_min}-{activity.temp_max} C",
                f"{activity.rain} mm",
                f"{activity.wind_min}-{activity.wind_max} km/h",
                f"{activity.time_range[0]}-{activity.time_range[1]}",
            )

    def add_activity(self) -> None:
        values = {
            "name": self.query_one("#act-name", Input).value.strip(),
            "temp_min": self.query_one("#act-tmin", Input).value.strip(),
            "temp_max": self.query_one("#act-tmax", Input).value.strip(),
            "rain": self.query_one("#act-rain", Input).value.strip(),
            "wind_min": self.query_one("#act-wmin", Input).value.strip(),
            "wind_max": self.query_one("#act-wmax", Input).value.strip(),
            "start": self.query_one("#act-start", Input).value.strip(),
            "end": self.query_one("#act-end", Input).value.strip(),
        }
        if not all(
            values[key] for key in ("name", "temp_min", "temp_max", "rain", "wind_max")
        ):
            self.notify("Fill in the required fields.", severity="error")
            return
        try:
            activity = self.app.weather_app.create_activity(
                values["name"],
                int(values["temp_min"]),
                int(values["temp_max"]),
                float(values["rain"]),
                float(values["wind_max"]),
                float(values["wind_min"] or 0),
                [values["start"] or "00:00", values["end"] or "23:59"],
            )
            self.app.weather_app.save_activity(activity)
        except Exception as exc:
            self.notify(str(exc), severity="error")
            return
        self.refresh_rows()
        self.notify(f"Saved {activity.name}.")

    def delete_selected(self) -> None:
        table = self.query_one("#activities-table", DataTable)
        row = table.cursor_row
        if row < 0 or row >= len(self._names):
            self.notify("Select an activity to delete.", severity="error")
            return
        name = self._names[row]
        self.app.weather_app.delete_activity(name)
        self.refresh_rows()
        self.notify(f"Deleted {name}.")


class SettingsScreen(Screen):
    """Edit app settings and clear local data."""

    BINDINGS = [("escape", "back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="settings-form"):
            yield Static("Settings", classes="title")
            yield Static("", id="env-note")
            yield Label("API key")
            yield Input(password=True, id="api-key")
            yield Label("Timezone")
            yield Input(value=self.app.config.timezone, id="timezone")
            yield Label("Log level")
            yield Input(value=self.app.config.log_level, id="log-level")
            yield Button("Save", id="save", variant="primary")
            yield Button("Clear cache", id="clear-cache")
            yield Button("Clear logs", id="clear-logs")
            yield Button("Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#api-key", Input).value = self.app.config.stored_api_key
        if os.getenv("OWM_API_KEY"):
            self.query_one("#env-note", Static).update(
                "OWM_API_KEY is set in the environment and overrides the saved key."
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "back":
            self.app.pop_screen()
        elif button_id == "save":
            api_key = self.query_one("#api-key", Input).value.strip()
            if not api_key:
                self.notify("API key is required.", severity="error")
                return
            try:
                _save_settings(
                    self.app,
                    api_key,
                    self.query_one("#timezone", Input).value,
                    self.query_one("#log-level", Input).value,
                )
            except CLIWeatherException as exc:
                self.notify(str(exc), severity="error")
                return
            self.app.switch_screen(MainScreen())
            self.notify("Settings saved.")
        elif button_id == "clear-cache":
            self.app.weather_app.clear_cache()
            self.notify("Cache cleared.")
        elif button_id == "clear-logs":
            self.app.weather_app.clear_logs()
            self.notify("Cleared logs.")

    def action_back(self) -> None:
        self.app.pop_screen()


class WeatherTUI(App):
    """Textual application for CLI Weather."""

    CSS = CSS
    TITLE = "CLI Weather"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, config_service: ConfigService | None = None):
        super().__init__()
        self.config = config_service or ConfigService()
        self.weather_app = self._build_weather_app()

    def _build_weather_app(self):
        from ..core.app import WeatherApp

        return WeatherApp(self.config)

    def rebuild_weather_app(self) -> None:
        self.weather_app = self._build_weather_app()

    def on_mount(self) -> None:
        if self.config.api_key:
            self.push_screen(MainScreen())
        else:
            self.push_screen(SetupScreen())

    def action_quit(self) -> None:
        self.exit()


def run() -> None:
    WeatherTUI().run()


if __name__ == "__main__":
    run()
