#!/data/data/com.termux/files/home/coding/andscripts/.venv/bin/python3
import sys
import requests
from pathlib import Path
from dotenv import dotenv_values
from datetime import datetime, timezone

# Load environment variables
VARS = dotenv_values()
API_KEY = VARS["API_KEY"]
COORDINATES = [key for key in VARS if key != "API_KEY"]
FORECAST_FILE = Path.home() / "storage/shared/emulated/0/Download/weather.txt"  # Forecast file location for Android.


def fetch_weather_data(lat, lon, api_key):
    """Fetch 5-day weather forecast data from OpenWeatherMap API."""
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        sys.exit(1)


def parse_weather_data(data):
    """Parse raw weather data into a list of daily summaries."""
    daily_weather = []
    for i in range(0, len(data['list']), 8):  # 8 intervals = 1 day
        forecast = data['list'][i]
        date = datetime.fromtimestamp(forecast['dt'], tz=timezone.utc).strftime('%Y-%m-%d')
        daily_weather.append({
            "date": date,
            "temp": forecast['main']['temp'],
            "weather": forecast['weather'][0]['description'],
            "wind_speed": forecast['wind']['speed'] * 3.6,  # Convert m/s to km/h
            "rain": forecast.get('rain', {}).get('3h', 0)  # Default to 0 if no rain
        })
    return daily_weather


def filter_best_weather(daily_weather):
    """Filter and rank days with the best weather."""
    best_days = [
        day for day in daily_weather
        if 18 <= day['temp'] <= 25 and day['rain'] < 1 and day['wind_speed'] <= 10
    ]
    if not best_days:
        best_days = [
            day for day in daily_weather
            if 15 <= day['temp'] <= 28 and day['rain'] < 5 and day['wind_speed'] <= 15
        ]
    return sorted(
        best_days,
        key=lambda x: (abs(22 - x['temp']), x['rain'], x['wind_speed'])
    )[:5]


def display_weather(daily_weather, best_days):
    """Display the weather forecast and best weather days."""
    print("\nWeather Forecast:")
    for day in daily_weather:
        print(f"Date: {day['date']}, Temp: {day['temp']}°C, Weather: {day['weather'].capitalize()}, "
              f"Wind: {day['wind_speed']:.2f} km/h, Rain: {day['rain']} mm")
    
    print("\nBest Weather Days:")
    for day in best_days:
        print(f"Date: {day['date']}, Temp: {day['temp']}°C, Weather: {day['weather'].capitalize()}, "
              f"Wind: {day['wind_speed']:.2f} km/h, Rain: {day['rain']} mm")


def save_weather_to_file(daily_weather, best_days):
    """Save the weather forecast and best days to a file."""
    with open(FORECAST_FILE, 'w') as file:
        file.write("Weather Forecast:\n")
        for day in daily_weather:
            file.write(f"Date: {day['date']}, Temp: {day['temp']}°C, Weather: {day['weather'].capitalize()}, "
                       f"Wind: {day['wind_speed']:.2f} km/h, Rain: {day['rain']} mm\n")
        
        file.write("\nBest Weather Days:\n")
        for day in best_days:
            file.write(f"Date: {day['date']}, Temp: {day['temp']}°C, Weather: {day['weather'].capitalize()}, "
                       f"Wind: {day['wind_speed']:.2f} km/h, Rain: {day['rain']} mm\n")
    print("Weather forecast saved to 'weather_forecast.txt'")


def get_coordinates():
    """Prompt the user to choose a coordinate."""
    print("Select a location:")
    for index, name in enumerate(COORDINATES, start=1):
        print(f"{index}. {name}")
    while True:
        try:
            choice = int(input("> "))
            if 1 <= choice <= len(COORDINATES):
                return [coord.strip() for coord in VARS[COORDINATES[choice - 1]].split(",")]
            print("Invalid choice. Please select a valid number.")
        except ValueError:
            print("Please enter a number.")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            sys.exit(0)


def main():
    lat, lon = get_coordinates()
    raw_data = fetch_weather_data(lat, lon, API_KEY)
    daily_weather = parse_weather_data(raw_data)
    best_days = filter_best_weather(daily_weather)
    display_weather(daily_weather, best_days)
    
    save = input("\nDo you want to save this forecast to a file? (yes/no): ").strip().lower()
    if save in ['yes', 'y']:
        save_weather_to_file(daily_weather, best_days)


if __name__ == "__main__":
    main()