# CLI Weather

[![CI](https://github.com/Onehand-Coding/cli-weather/actions/workflows/ci.yml/badge.svg)](https://github.com/Onehand-Coding/cli-weather/actions/workflows/ci.yml)

A Textual terminal UI for current weather, forecasts, activity planning, and
typhoon alerts. It also keeps a Typer CLI for scripting.

## Features

- Textual TUI with setup, weather, locations, activities, and settings screens.
- Current weather, 24-hour forecast, 5-day forecast, and specific-day forecast.
- Best-day recommendations for saved activities.
- Typhoon and weather alerts.
- Saved locations and activities in a single config file.
- Typer CLI for automation.
- Rich and legacy menus remain available as fallbacks.

## Install

Requirements: Python 3.10+ and [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/Onehand-Coding/cli-weather.git
cd cli-weather
uv sync --extra dev
uv run cli-weather
```

On first launch the TUI asks for an OpenWeatherMap API key and saves it to your
config file.

## Configuration

Configuration is app-managed. There is no `.env` file.

- Config: `~/.config/cli-weather/config.json`
- Cache: `~/.cache/cli-weather`
- Logs: `~/.local/state/cli-weather/logs`
- Data: `~/.local/share/cli-weather`

The config file stores the API key, timezone, log level, locations, and
activities. On POSIX systems it is written with mode `0600`.

Overrides:

```bash
CLI_WEATHER_CONFIG_DIR=/path/to/config
CLI_WEATHER_CACHE_DIR=/path/to/cache
CLI_WEATHER_LOG_DIR=/path/to/logs
CLI_WEATHER_DATA_DIR=/path/to/data
OWM_API_KEY=your_key
```

`OWM_API_KEY` is optional and is intended for automation. When set, it takes
precedence over the saved key. The TUI Settings screen shows a notice when the
environment override is active and never copies the environment value into the
config file.

## TUI

```bash
uv run cli-weather
```

Screens:

- **Setup**: first-run API key, timezone, and log level.
- **Weather**: choose a forecast type, saved location, current location, or
  manual coordinates; load results into a table.
- **Locations**: add by address or coordinates, and delete saved locations.
- **Activities**: add weather criteria for an activity, and delete activities.
- **Settings**: edit the API key, timezone, and log level; clear cache or logs.

Keyboard: `q` quits from the main screen, `Escape` goes back, and `s` opens
Settings from the main screen.

## CLI

```bash
uv run cli-weather --cli weather current --current
uv run cli-weather weather daily --location "New York"
uv run cli-weather weather hourly --lat 40.7128 --lon -74.0060
uv run cli-weather weather activity hiking --current
uv run cli-weather weather alerts --current
uv run cli-weather location list
uv run cli-weather activity list
uv run cli-weather config clear-cache
```

Run `uv run cli-weather --cli --help` for the full command list.

## Other Interfaces

```bash
uv run cli-weather --rich     # Rich menu
uv run cli-weather --legacy   # Original menu
```

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

CI runs the same commands plus a wheel build and a TUI package check.

## Architecture

```text
src/cli_weather/
  core/                 services and app orchestration
  ui/tui.py             Textual TUI
  ui/typer_cli.py       Typer CLI
  ui/rich_ui.py         Rich menu
  legacy/               legacy UI and shared storage helpers
```

The TUI talks to `WeatherApp`, which composes the weather, location, activity,
and cache services. The config file is the single source of truth for settings,
locations, and activities.

## Troubleshooting

- **Missing API key:** open Settings in the TUI and save a key.
- **No weather data:** check the API key, network connection, and location.
- **Old `.env` file:** it is ignored. Move the key into the TUI Settings screen
  or `config.json`.
- **No map/address:** geocoding is network-dependent and may be rate-limited.

## License

MIT. See `LICENSE`.
