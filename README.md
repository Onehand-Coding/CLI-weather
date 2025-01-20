# CLI Weather - A simple text based weather app in python that uses Openweathermap API to fetch weather data.

CLI Weather is a command-line application that provides weather information, forecasts, and activity recommendations based on the user's location. It allows users to view current weather, hourly forecasts, and multi-day forecasts. Additionally, it provides functionality for managing user-defined locations, activities and saving their current location.

## Features:
- View current weather in chosen location.
- View hourly forecast in chosen location.
- View 5-day forecast in chosen location.
- View best days for an activity based on criteria set by user.
- Manage saved activities (view, add, edit, delete)
- Manage saved locations (view, add, delete)

## Requirements:
- Python 3.x
- External weather API (e.g., OpenWeatherMap)

## Installation:
1. Clone the repository.
2. Install the required dependencies: `pip install -r requirements.txt`.
3. Create .env file to place sensitive information: API KEY, sensitive locations and activities(Optional but recommended).

## Usage:
To run the application, navigate to project root folder and execute the following command:
python -m cli_weather.main
