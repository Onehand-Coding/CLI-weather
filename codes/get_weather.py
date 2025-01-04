#!/data/data/com.termux/files/home/coding/andscripts/.venv/bin/python3
import sys
import requests
from pathlib import Path
from dotenv import dotenv_values
from datetime import datetime, timezone

# Load environment variables
VARS = dotenv_values()
API_KEY = VARS["API_KEY"]
COORDINATE_KEYS = [key for key in VARS if key != "API_KEY"]
ACTIVITIES = ["farming", "fishing"]


def get_index(items):
    while True:
        try:
            index = int(input("> "))
            if 1 <= index <=len(items):
                return index - 1
        except ValueError:
            print("Please enter an integer.")
        except KeyboardInterrupt:
            print("Operation cancelled.")
            sys.exit()


def get_activity():
    print("Choose an activity.")
    for i, activity in enumerate(ACTIVITIES, start=1):
        print(i, activity)
    return ACTIVITIES[get_index(ACTIVITIES)]


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


def filter_best_days(daily_weather, activity):
    """Filter and rank days with the best weather for an activity."""
    if activity == "fishing":
        criteria = lambda day: (
            19 <= day['temp'] <= 30 and day['rain'] < 1 and day['wind_speed'] <= 15
        )
    elif activity == "farming":
        criteria = lambda day: (
            19 <= day['temp'] <= 30 and day['rain'] < 1 and day['wind_speed'] <= 20
        )
    else:
        return []

    best_days = [day for day in daily_weather if criteria(day)]
    return sorted(
        best_days,
        key=lambda x: (abs(22 - x['temp']), x['rain'], x['wind_speed'])
    )[:5]


def display_weather(daily_weather, activity, best_activity_days):
    """Display the weather forecast and best weather days for an activity."""
    print("\nWeather Forecast:")
    for day in daily_weather:
        print(f"Date: {day['date']}, Temp: {day['temp']}°C, Weather: {day['weather'].capitalize()}, "
              f"Wind: {day['wind_speed']:.2f} km/h, Rain: {day['rain']} mm")
    
    print(f"\nBest {activity.capitalize} Days:")
    for day in best_activity_days:
        print(f"Date: {day['date']}, Temp: {day['temp']}°C, Weather: {day['weather'].capitalize()}, "
              f"Wind: {day['wind_speed']:.2f} km/h, Rain: {day['rain']} mm")


def save_weather_to_file(location_name, daily_weather, activity, best_activity_days):
    """Save the weather forecast and best days to a file."""
    forecast_file = Path.home() / f"storage/shared/Download/weather_{location_name}.txt"
    with open(forecast_file, 'w') as file:
        file.write("Weather Forecast:\n")
        for day in daily_weather:
            file.write(f"Date: {day['date']}, Temp: {day['temp']}°C, Weather: {day['weather'].capitalize()}, "
                       f"Wind: {day['wind_speed']:.2f} km/h, Rain: {day['rain']} mm\n")
        
        file.write(f"\nBest {activity.capitalize} Days:\n")
        for day in best_activity_days:
            file.write(f"Date: {day['date']}, Temp: {day['temp']}°C, Weather: {day['weather'].capitalize()}, "
                       f"Wind: {day['wind_speed']:.2f} km/h, Rain: {day['rain']} mm\n")

    print(f"Weather forecast saved to '{forecast_file}'")


def get_coordinates():
    """Prompt the user to choose a coordinate."""
    print("Select a location:")
    for index, name in enumerate(COORDINATE_KEYS, start=1):
        print(f"{index}. {name}")
    
    return name, [coord.strip() for coord in VARS[COORDINATE_KEYS[get_index(COORDINATE_KEYS)]].split(",")]


def main():
    activity = get_activity()
    location_name, (lat, lon) = get_coordinates()
    raw_data = fetch_weather_data(lat, lon, API_KEY)
    daily_weather = parse_weather_data(raw_data)
    best_activity_days = filter_best_days(daily_weather, activity)
    display_weather(daily_weather, activity, best_activity_days)
    
    save = input("\nDo you want to save this forecast to a file? (yes/no): ").strip().lower()
    if save in ['yes', 'y']:
        save_weather_to_file(location_name, activity, daily_weather, best_activity_days)


if __name__ == "__main__":
    main()