# CLI Weather TUI and Config Storage Design

Date: 2026-11-01
Status: Approved for implementation
Repo: https://github.com/Onehand-Coding/cli-weather

## Context

The repository currently has a rich interactive menu, a Typer CLI, and a legacy
menu. It reads `.env` through `python-dotenv`, writes data under the project
directory, and mixes legacy config modules into the core services.

Known problems:

- `python-dotenv` reads `.env` in two places, and the README teaches users to
  create one.
- `ConfigService` and `legacy/config.py` duplicate config logic and both use
  project-local `data/`, `logs/`, and `data/cache/` directories.
- The API key is a module-level constant in several places, so changing it at
  runtime is awkward.
- `WeatherService` reads `LOCAL_TIMEZONE` directly from the legacy module.
- `WeatherApp` imports legacy `API_KEY`, `CACHED_DIR`, `CACHE_EXPIRY`, and
  `LOG_DIR`.
- The default UI is a menu of rich prompts, not a real TUI.
- The existing tests cover the services but there are no TUI tests and no CI.

## Goals

1. Make a Textual TUI the default interface.
2. Replace `.env` with an app-managed config file in the XDG config directory.
3. Store the API key, timezone, log level, locations, and activities in one
   JSON config file with restrictive permissions.
4. Remove `python-dotenv` and project-local runtime directories.
5. Keep the Typer CLI available for automation.
6. Add TUI, storage, and wiring tests, plus CI and accurate docs.

## Non-goals

- Removing the Typer CLI.
- Removing the legacy UI, which remains an optional fallback.
- Replacing the weather API or adding new weather providers.
- OS keyring integration.
- Reworking the weather data model beyond what the TUI needs.

## Storage

Use XDG-style directories with environment overrides:

```text
Config:  ${XDG_CONFIG_HOME:-~/.config}/cli-weather/config.json
Cache:   ${XDG_CACHE_HOME:-~/.cache}/cli-weather
Logs:    ${XDG_STATE_HOME:-~/.local/state}/cli-weather/logs
Data:    ${XDG_DATA_HOME:-~/.local/share}/cli-weather
```

Overrides:

- `CLI_WEATHER_CONFIG_DIR`
- `CLI_WEATHER_CACHE_DIR`
- `CLI_WEATHER_LOG_DIR`
- `CLI_WEATHER_DATA_DIR`
- `OWM_API_KEY` (optional environment override for automation)

Config shape:

```json
{
  "api_key": "",
  "timezone": "UTC",
  "log_level": "ERROR",
  "locations": {"Manila": "14.5987713, 120.9833966"},
  "activities": {"walking": {"temp_min": 18, "temp_max": 30, "rain": 0.0, "wind_min": 0, "wind_max": 10.0, "time_range": ["00:00", "23:59"]}}
}
```

- The config directory is created with mode `0700`.
- The config file is written with mode `0600` where the platform supports it.
- Reads never create files.
- Writes create parent directories lazily.
- Invalid JSON falls back to defaults and logs an error.
- `.env` is no longer read. `python-dotenv` is removed from dependencies.

## Architecture

`src/cli_weather/legacy/config.py` becomes the low-level storage module used by
existing services and tests. It exposes the same `load_config`, `save_config`,
`configure_logging`, and constants, but no longer imports `dotenv`.

`src/cli_weather/core/config_service.py` becomes a small service wrapper around
the same storage. It exposes:

- `api_key`, `timezone`, `log_level`, `cache_expiry`
- `load_config`, `save_config`
- `get_locations`, `save_location`, `delete_location`
- `get_activities`, `save_activity`, `delete_activity`
- `setup_logging`

`WeatherApp` accepts an optional `ConfigService`, builds a cache manager from the
new cache directory, and passes the API key and timezone into `WeatherService`.
`WeatherService` accepts a `timezone` argument and never imports legacy config
constants.

`LocationService` and `ActivityService` keep using the legacy config
`load_config`/`save_config` functions, which now read and write the new config
file. This preserves their public API and most existing tests.

## TUI

Create `src/cli_weather/ui/tui.py` using Textual.

Screens:

- `SetupScreen`: shown when the API key is missing. Inputs for API key
  (password), timezone, and log level. Save writes the config and opens the main
  screen.
- `MainScreen`: buttons for Weather, Locations, Activities, Settings, and Quit.
  Shows whether an API key is configured.
- `WeatherScreen`: forecast type select (Current, Hourly, 5-Day, Specific Day,
  Best Activity Day, Typhoon Alerts), saved-location select, optional day and
  activity inputs, manual latitude/longitude inputs, Load button, and a
  `DataTable` or `RichLog` for results.
- `LocationsScreen`: table of saved locations, add-by-address, add-by-coordinate,
  delete-selected, and refresh.
- `ActivitiesScreen`: table of activities, add form with temperature, rain, wind,
  and time-range fields, delete-selected, and refresh.
- `SettingsScreen`: edit API key, timezone, and log level; save; clear cache;
  clear logs.

Behavior:

- No network calls on startup.
- API calls run in Textual workers so the UI remains responsive.
- Errors use Textual notifications.
- After settings save, the TUI rebuilds `WeatherApp` so the new key is used.
- `q` quits from the main screen; `Escape` goes back.
- The TUI uses `WeatherApp` for weather, locations, activities, and typhoons.

## Entry point

- No arguments: launch the Textual TUI.
- `--tui`: launch the TUI.
- `--rich`: launch the existing rich UI.
- `--legacy`: launch the legacy UI.
- `--cli` or a known command (`weather`, `location`, `activity`, `config`):
  launch the Typer CLI.
- `--help`/`help`: print the mode summary.

## Tests

- Storage tests: default paths, environment overrides, load/save round trip,
  permissions where supported, missing and invalid files, API key env override,
  timezone/log level defaults.
- Core tests: `WeatherService` timezone argument, `WeatherApp` uses
  `ConfigService`, cache dir and log dir wiring.
- TUI tests using Textual `run_test`:
  - no API key opens `SetupScreen`
  - a saved API key opens `MainScreen`
  - settings save updates the config file
  - main menu navigation opens the weather, locations, activities, and settings
    screens
  - weather results render in the table with a mocked `WeatherApp`
- Existing service and CLI tests must continue to pass after import/patch updates.
- Add `tests/conftest.py` to isolate config/cache/log/data directories in a temp
  directory before modules import.

## Tooling and CI

- Add `textual>=8.0.0`.
- Remove `python-dotenv`.
- Add `pytest` and `ruff` configuration.
- Add `.github/workflows/ci.yml` running:
  - `uv sync --extra dev`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run pytest`
  - `uv build` and a package-content check.
- README:
  - TUI screenshots or a text walkthrough (no binary required).
  - Config file location and environment overrides.
  - Remove `.env` instructions.
  - Document TUI, CLI, and legacy modes.
- `CONTEXT.md` with architecture, storage, commands, and gotchas.

## Acceptance criteria

1. No `python-dotenv` import or `.env` read remains.
2. `cli-weather` with no arguments opens the Textual TUI.
3. First run without an API key shows setup and saves the key to the XDG config
   file with mode `0600`.
4. Weather, locations, activities, settings, and typhoon actions are reachable
   from the TUI.
5. The Typer CLI still works with the new config.
6. Cache, logs, and config are outside the project directory.
7. `ruff check`, `ruff format --check`, and `pytest` pass locally and in CI.
8. README and CONTEXT match the implementation.

## Risks and mitigations

- Textual API drift. Pin `textual>=8.0.0` and cover core screens with `run_test`.
- Test isolation. Set config/cache/log/env overrides in `conftest.py` before
  service imports.
- Existing tests patch legacy modules. Keep the legacy config API shape and
  default `CONFIG_FILE` behavior so patches continue to work.
- Network calls in the TUI. Use workers and mock them in tests.
- Secrets in config. Use `0600` permissions and never log the API key (existing
  `WeatherService` logs the key on 401; remove that).
