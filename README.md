# CLI Weather - Your Command-Line Weather Companion

CLI Weather is a versatile command-line application built with Python that provides current weather information, detailed forecasts, and personalized activity recommendations. It leverages the OpenWeatherMap API to fetch up-to-date weather data and offers multiple user interfaces to suit different use cases.

This project follows modern Python architecture with clean separation of concerns, multiple UI implementations, and is optimized for use with the uv package manager.

## Features

* **Current Weather:** Get real-time weather conditions for any chosen location.
* **Hourly Forecasts:** View weather predictions for the next 24 hours.
* **5-Day Forecasts:** Plan ahead with a 5-day weather outlook.
* **Specific Day Forecast:** Get detailed weather for a particular day within the 5-day range.
* **Activity-Based Recommendations:** Discover the best days for your favorite activities based on customizable weather criteria (e.g., temperature, rain, wind, time of day).
* **Typhoon Tracking & Alerts:** View active weather alerts, including typhoon warnings, for your chosen location and save them to a file.
* **Location Management:**
    * Save and manage a list of your favorite locations.
    * Add new locations by name or coordinates.
    * Automatically fetch and save your current location.
    * Search for locations globally.
* **Activity Management:**
    * Define and customize weather criteria for different activities (e.g., walking, fishing).
    * View, add, edit, and delete your saved activities.
* **Data Management:**
    * Cache weather data locally to improve performance and reduce API calls.
    * Option to clear cached data.
    * Option to clear application logs.
* **Save Forecasts:** Save weather forecasts to a text file for offline viewing.

## Requirements

* Python 3.10+
* An OpenWeatherMap API Key
* Dependencies are managed in pyproject.toml and include:
    * geopy - Location geocoding and geospatial calculations
    * python-dotenv - Environment variable management
    * requests - HTTP client for weather API calls
    * tzdata - Timezone data
    * rich - Enhanced terminal output with modern styling
    * typer - Command-line interface framework

## Installation

This project is managed with uv for modern Python dependency management.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Onehand-Coding/cli-weather.git
   cd cli-weather
   ```

2. **Install with uv (recommended):**
   ```bash
   uv sync
   ```
   This command automatically creates a virtual environment, installs all dependencies, and sets up the project in editable mode.

### Alternative Installation (Traditional Method)

If you prefer to use standard Python tools:

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv

   # On Linux/macOS
   source .venv/bin/activate

   # On Windows
   .\.venv\Scripts\activate
   ```

2. **Install the project in editable mode:**
   ```bash
   pip install -e .
   ```

## Configuration

### API Key Setup

This application requires an API key from [OpenWeatherMap](https://openweathermap.org/api) to fetch weather data.

1. Sign up for a free account on OpenWeatherMap and obtain your API key.
2. Create a `.env` file in the root directory of the project (`cli-weather/.env`).
3. Add your API key to the `.env` file like this:
   ```
   OWM_API_KEY=your_actual_api_key_here
   ```

### Other Environment Variables (Optional)

You can also set the following optional environment variables in your `.env` file:

* `TZ`: Set your local timezone (e.g., `Asia/Manila`). Defaults to `UTC` if not set.
* `LOG_LEVEL`: Set the logging level (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`). Defaults to `ERROR`.
* You can also define sensitive locations directly in the `.env` file using a custom name and comma-separated coordinates, for example:
  ```
  MY_SECRET_SPOT=12.345,67.890
  ```

### Application Data

* **Configuration File (`data/config.json`):** Stores your saved locations and activity criteria. This file is automatically created and managed by the application.
* **Cache (`data/cache/`):** Weather data is cached here to speed up requests and reduce API usage. Cache expires after 30 minutes.
* **Logs (`logs/weather_app.log`):** Application logs are stored here.

## Usage

CLI Weather offers multiple user interfaces to suit different workflows and preferences:

### 🎨 Rich Interactive UI (Default)

Launches a modern, interactive menu system with enhanced visuals, tables, progress bars, and styled output:

```bash
uv run cli-weather                    # Default mode
# or
uv run python -m cli_weather
# or
cli-weather                           # If installed with pip
```

### ⚡ Command Line Interface (Typer)

For automation, scripting, and direct command execution:

```bash
# Weather commands
uv run cli-weather weather current --current
uv run cli-weather weather daily --location "New York"
uv run cli-weather weather hourly --lat 40.7128 --lon -74.0060
uv run cli-weather weather day 3 --location "Denver" --hourly
uv run cli-weather weather activity hiking --current
uv run cli-weather weather alerts --current

# Location management
uv run cli-weather location list
uv run cli-weather location add "Home" --lat 40.7128 --lon -74.0060
uv run cli-weather location current --name "My Location"
uv run cli-weather location search "Tokyo"

# Activity management
uv run cli-weather activity list
uv run cli-weather activity add "jogging" --temp-min 15 --temp-max 25 --rain 0
uv run cli-weather activity show hiking

# Configuration
uv run cli-weather config clear-cache
uv run cli-weather config clear-logs
```

### 🔄 Legacy Mode

For backwards compatibility with the original interface:

```bash
uv run cli-weather --legacy
```

### 📋 Command Line Options

**Common Location Options:**
- `--location NAME` or `-l NAME`: Use a saved location
- `--current` or `-c`: Auto-detect current location via IP
- `--lat LAT --lon LON`: Use specific coordinates

**Output Options:**
- `--json`: Output data in JSON format (CLI mode only)
- `--output FILE` or `-o FILE`: Save results to file
- `--hours N`: Number of hours for hourly forecasts (1-120)
- `--hourly`: Show hourly details for specific day forecasts

**Activity Options:**
- `--temp-min N`: Minimum temperature in Celsius
- `--temp-max N`: Maximum temperature in Celsius
- `--rain N`: Maximum rainfall in mm
- `--wind-min N`: Minimum wind speed in km/h
- `--wind-max N`: Maximum wind speed in km/h
- `--start HH:MM`: Activity start time
- `--end HH:MM`: Activity end time

**Examples:**

```bash
# Get current weather for saved location
uv run cli-weather weather current -l "New York"

# Get 5-day forecast for current location
uv run cli-weather weather daily --current

# Get specific day with hourly details
uv run cli-weather weather day 2 --current --hourly

# Find best days for activity with JSON output
uv run cli-weather weather activity hiking --current --json

# Get hourly forecast and save to file
uv run cli-weather weather hourly --lat 35.6762 --lon 139.6503 -o forecast.txt

# Add location by address geocoding
uv run cli-weather location add "Office" --address "Times Square, New York"
```

### 💡 Getting Help

```bash
# General help
uv run cli-weather --help

# Command-specific help
uv run cli-weather weather --help
uv run cli-weather location --help
uv run cli-weather activity --help
```

## Architecture

CLI Weather follows a clean, modular architecture with clear separation of concerns:

### 🏗️ Project Structure

```
src/cli_weather/
├── core/                    # Pure business logic (no UI concerns)
│   ├── app.py              # Main app orchestrator
│   ├── weather_service.py   # Weather API and data processing
│   ├── location_service.py  # Location management and geocoding
│   ├── activity_service.py  # Activity criteria management
│   ├── config_service.py    # Configuration management
│   ├── cache_service.py     # Data caching
│   ├── models.py           # Data models (Location, Activity, WeatherData)
│   └── exceptions.py       # Custom exceptions
├── ui/                     # UI layer (multiple implementations)
│   ├── rich_ui.py          # Rich-based interactive UI
│   └── typer_cli.py        # Typer-based command-line UI
├── legacy/                 # Original mixed-concern modules
└── __main__.py             # Main entry point with UI selection
```

### 🧩 Core Principles

1. **Separation of Concerns**: Business logic is completely isolated from UI concerns
2. **Multiple UI Support**: Same core functionality accessible through different interfaces
3. **Dependency Injection**: Services are injected rather than directly instantiated
4. **Clean Data Models**: Well-defined data structures for all entities
5. **Comprehensive Testing**: Full test coverage of business logic with proper mocking
6. **Error Handling**: Consistent error handling across all layers

### 📊 Data Flow

```
UI Layer → App Orchestrator → Services → External APIs/Storage
  │              │              │              │
 Rich UI       WeatherApp    Weather     OpenWeatherMap
 Typer CLI                   Location    Nominatim
 Legacy UI                   Activity    Config Files
                             Cache       File System
```

### 🔌 Services Overview

- **WeatherService**: Handles all weather-related operations (API calls, data parsing, caching)
- **LocationService**: Manages locations (geocoding, IP-based detection, persistence)
- **ActivityService**: Manages activity criteria and weather filtering
- **ConfigService**: Handles configuration persistence and retrieval
- **CacheService**: Manages data caching with expiration

## Running Tests

The test suite covers all core business logic with comprehensive mocking:

```bash
# Run all tests
uv run python -m unittest discover tests

# Run specific test files
uv run python -m unittest tests.test_services  # Core services
uv run python -m unittest tests.test_ui        # UI components
uv run python -m unittest tests.test_core      # Legacy tests

# Or without uv
python -m unittest discover tests
```

## License

This project is licensed under the MIT License.

## Author

Onehand Coding (onehand.coding433@gmail.com)
GitHub Repository: [https://github.com/Onehand-Coding/CLI-weather](https://github.com/Onehand-Coding/CLI-weather)
