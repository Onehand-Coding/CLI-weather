# Project Context

## Purpose

A local Textual TUI for weather, forecasts, activity planning, and typhoon
alerts. It keeps a Typer CLI for automation.

## Architecture

- `ui/tui.py` is the default Textual interface: setup, main, weather, locations,
  activities, and settings screens.
- `core/app.py` (`WeatherApp`) composes weather, location, activity, and cache
  services for the TUI and CLI.
- `core/config_service.py` is the app-facing settings service.
- `legacy/config.py` is the low-level XDG JSON store shared by the core and the
  legacy UI.
- `ui/typer_cli.py` is the scripting interface.
- `ui/rich_ui.py` and `legacy/` are optional fallbacks.

## Storage

- Config: `${XDG_CONFIG_HOME:-~/.config}/cli-weather/config.json`
- Cache: `${XDG_CACHE_HOME:-~/.cache}/cli-weather`
- Logs: `${XDG_STATE_HOME:-~/.local/state}/cli-weather/logs`
- Data: `${XDG_DATA_HOME:-~/.local/share}/cli-weather`

Overrides: `CLI_WEATHER_CONFIG_DIR`, `CLI_WEATHER_CACHE_DIR`,
`CLI_WEATHER_LOG_DIR`, `CLI_WEATHER_DATA_DIR`, and optional `OWM_API_KEY`.

The config file holds `api_key`, `timezone`, `log_level`, `locations`, and
`activities`. It is written with mode `0600` on POSIX. No `.env` file is read.

## Commands

```bash
uv sync --extra dev
uv run cli-weather                 # TUI
uv run cli-weather --cli weather current --current
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Decisions

- Textual is the default interface.
- The app owns its config file instead of reading `.env`.
- Keep the legacy config API shape so existing services and tests continue to
  work.
- Keep the Typer CLI and the Rich/legacy menus as fallbacks.
- Use workers for network calls so the TUI remains responsive.

## Gotchas

- `legacy/config.py` constants are computed at import from the environment;
  `ConfigService` reads paths dynamically so tests can override them.
- `ConfigService(config_dir=...)` isolates the config file for tests.
- `OWM_API_KEY` overrides the saved key for automation.
- Settings save rebuilds `WeatherApp` so the new key and timezone are used.
- The TUI tests use Textual `run_test` and `asyncio.run`.
- Do not log API keys; the 401 path now logs only a generic message.

## Known Limitations

- Location and activity services still use the legacy config functions, which
  share the same config file.
- Geocoding and weather data require network access.
- The Rich and legacy menus are not the primary interface and receive less test
  coverage.
