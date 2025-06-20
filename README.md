# CLI Weather - Your Command-Line Weather Companion

CLI Weather is a versatile command-line application built with Python that provides current weather information, detailed forecasts, and personalized activity recommendations. It leverages the OpenWeatherMap API to fetch up-to-date weather data and offers a user-friendly interface to manage locations and activities.

This project is structured using modern Python standards, including a src layout and pyproject.toml for dependency management, and is optimized for use with the uv package manager.

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

* Python 3.7+
* An OpenWeatherMap API Key
* Dependencies are managed in pyproject.toml and include:
    * geopy
    * python-dotenv
    * requests
    * tzdata

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

Once installed, you can run the application with the uv run command:

```bash
uv run cli-weather
```

Alternatively, you can run the application as a module:

```bash
uv run python -m cli_weather
```

### Alternative Usage (without uv)

If you have installed the package using `pip install .`, you can run the application with:
```bash
cli-weather
```

Alternatively, you can run it directly from the project's root directory:
```bash
python -m cli_weather
```

The application will then present you with a menu of options to navigate.

## Running Tests

To run the unit tests for this project, navigate to the project root folder and execute:

```bash
uv run python -m unittest discover tests
```

Or without uv:
```bash
python -m unittest tests.test_core
```

## License

This project is licensed under the MIT License.

## Author

Onehand Coding (onehand.coding433@gmail.com)
GitHub Repository: [https://github.com/Onehand-Coding/CLI-weather](https://github.com/Onehand-Coding/CLI-weather)
