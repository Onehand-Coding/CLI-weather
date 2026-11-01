# CLI Weather TUI and Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `.env`-driven rich menu with a Textual TUI and an XDG JSON config file, while keeping the Typer CLI and legacy UI working.

**Architecture:** `legacy/config.py` becomes the low-level XDG JSON store. `ConfigService` wraps it for the core/TUI. `WeatherApp` uses `ConfigService` for the API key, timezone, cache, and logs. `ui/tui.py` is a Textual app with setup, main, weather, locations, activities, and settings screens.

**Tech Stack:** Python 3.10+, Textual 8, Rich, Typer, geopy, requests, pytest, ruff, uv, GitHub Actions.

**Git policy:** Do not run `git commit`, `git push`, or `git add` unless the user explicitly asks.

---

## Task 1: XDG Config Storage

**Files:**
- Replace: `src/cli_weather/legacy/config.py`
- Replace: `src/cli_weather/core/config_service.py`
- Modify: `src/cli_weather/legacy/utils.py`
- Modify: `src/cli_weather/core/weather_service.py`
- Modify: `src/cli_weather/core/app.py`
- Modify: `pyproject.toml`
- Create: `tests/conftest.py`
- Create: `tests/test_config_storage.py`

- [ ] **Step 1: Write storage tests**

`tests/conftest.py`:

```python
import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="cli-weather-tests-"))
os.environ.setdefault("CLI_WEATHER_CONFIG_DIR", str(_TMP / "config"))
os.environ.setdefault("CLI_WEATHER_CACHE_DIR", str(_TMP / "cache"))
os.environ.setdefault("CLI_WEATHER_LOG_DIR", str(_TMP / "logs"))
os.environ.setdefault("CLI_WEATHER_DATA_DIR", str(_TMP / "data"))
```

`tests/test_config_storage.py`:

```python
import json
import os
import stat
from pathlib import Path

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
    service = ConfigService(tmp_path)
    from cli_weather.core.models import Location, Activity

    service.save_location(Location("Home", 1.0, 2.0))
    service.save_activity(
        Activity("walk", 10, 20, 1.0, 0, 10.0, ("06:00", "18:00"))
    )

    assert service.get_locations()["Home"].latitude == 1.0
    assert service.get_activities()["walk"].temp_max == 20
```

- [ ] **Step 2: Replace `legacy/config.py`**

Use XDG paths with env overrides, JSON config, and lazy writes. Keep `load_config`, `save_config`, `configure_logging`, constants, and `VARS = {}`.

- [ ] **Step 3: Replace `core/config_service.py`**

Wrap the storage functions and expose `api_key`, `timezone`, `log_level`, `cache_expiry`, `get_locations`, `save_location`, `delete_location`, `get_activities`, `save_activity`, `delete_activity`, `setup_logging`.

- [ ] **Step 4: Update core wiring**

- `legacy/utils.CacheManager.__init__`: create the cache directory lazily.
- `weather_service.WeatherService.__init__`: add `timezone="UTC"`, build `ZoneInfo` with a UTC fallback, replace `LOCAL_TIMEZONE` uses, and stop logging the API key on 401.
- `core/app.py`: accept `ConfigService | None`, build `CacheManager(config.cache_dir, config.cache_expiry)`, pass `config.api_key` and `config.timezone`, and use `config.log_dir` in `clear_logs`.

- [ ] **Step 5: Remove `python-dotenv`**

Delete it from `pyproject.toml` and run `uv sync --extra dev`. Remove `dotenv` imports from both config modules.

- [ ] **Step 6: Run storage and core tests**

```bash
uv run pytest tests/test_config_storage.py tests/test_services.py tests/test_core.py -q
```

Fix import/patch fallout until green.

---

## Task 2: Textual TUI

**Files:**
- Create: `src/cli_weather/ui/tui.py`
- Modify: `src/cli_weather/__main__.py`
- Create: `tests/test_tui.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add Textual**

Add `textual>=8.0.0` to dependencies. Run `uv sync --extra dev`.

- [ ] **Step 2: Implement `ui/tui.py`**

Screens:

- `SetupScreen`: API key (password), timezone, log level; Save; Quit.
- `MainScreen`: Weather, Locations, Activities, Settings, Quit; API key status.
- `WeatherScreen`: forecast select (Current, Hourly, 5-Day, Specific Day, Best Activity Day, Typhoon Alerts), location select, optional day/activity inputs, manual lat/lon, Load, Back; `DataTable` and `RichLog`.
- `LocationsScreen`: table, add by address, add by coordinates, delete selected, Back.
- `ActivitiesScreen`: table, add form, delete selected, Back.
- `SettingsScreen`: API key, timezone, log level, Save, Clear Cache, Clear Logs, Back.

Behavior:

- `WeatherTUI(config_service=None)` builds `ConfigService` and `WeatherApp`.
- `on_mount` pushes `SetupScreen` when the key is missing, otherwise `MainScreen`.
- Weather/geocoding calls run in `@work(thread=True)` workers and update widgets with `call_from_thread`.
- Errors use `self.notify(..., severity="error")`.
- Settings save writes the config and rebuilds `WeatherApp`.
- `q` quits; `Escape` goes back.

- [ ] **Step 3: Add TUI tests**

`tests/test_tui.py`:

```python
import asyncio
from pathlib import Path

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

        assert ConfigService(tmp_path).api_key == "new"
        assert ConfigService(tmp_path).timezone == "Asia/Manila"

    asyncio.run(scenario())
```

Add a mocked weather-screen test once the screen is implemented.

---

## Task 3: Entry Point and CLI

**Files:**
- Modify: `src/cli_weather/__main__.py`
- Modify: `tests/test_ui.py` or add `tests/test_entrypoint.py`

- [ ] **Step 1: Make TUI the default**

- No args -> `run_tui()`.
- `--tui` -> TUI.
- `--rich` -> existing rich UI.
- `--legacy` -> legacy UI.
- `--cli` or a known command -> Typer CLI.
- `--help`/`help` -> mode summary.

- [ ] **Step 2: Add entry-point tests**

Use `unittest.mock.patch` on `run_tui`, `run_typer_cli`, `run_rich_ui`, and `run_legacy_ui`, then call `main()` with patched `sys.argv`.

---

## Task 4: CI, Docs, and Final Verification

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `README.md`
- Create: `CONTEXT.md`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add pytest/Ruff config and CI**

Add `[tool.pytest.ini_options]`, keep Ruff config, and add a workflow running `uv sync --extra dev`, `ruff check`, `ruff format --check`, `pytest`, and `uv build`.

- [ ] **Step 2: Update README**

- Textual TUI is the default.
- Config file: `~/.config/cli-weather/config.json`, mode `0600`.
- Remove all `.env` instructions.
- Document `CLI_WEATHER_*` overrides and `OWM_API_KEY`.
- Document the CLI and legacy modes.
- Document testing.

- [ ] **Step 3: Create `CONTEXT.md`**

Architecture, storage paths, TUI screens, commands, gotchas.

- [ ] **Step 4: Final verification**

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run pytest -q -W error
rm -rf dist build
uv build
python3 -m zipfile -l dist/*.whl | grep cli_weather/ui/tui.py
CLI_WEATHER_CONFIG_DIR=/tmp/cli-weather-verify uv run python -c "from cli_weather.core.config_service import ConfigService; print(ConfigService().config_file)"
grep -R "dotenv\|\.env" src || true
```

Expected: lint/format/tests pass, wheel contains the TUI, config path is outside the repo, and no `dotenv` or `.env` reads remain.

- [ ] **Step 5: Report status**

Files changed, test/lint results, unverified items.

Do not commit or push unless the user explicitly asks.
