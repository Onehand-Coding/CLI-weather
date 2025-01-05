#!/data/data/com.termux/files/home/coding/andscripts/.venv/bin/python3
import sys
import json
import requests
from pathlib import Path
from dotenv import dotenv_values
from datetime import datetime, timezone
from typing import List
from zoneinfo import ZoneInfo
import os
from collections import defaultdict

# Load environment variables
VARS = dotenv_values()
API_KEY = VARS["API_KEY"]
COORDINATE_KEYS = [key for key in VARS if key != "API_KEY"]
ACTIVITIES = ["farming", "fishing"]
CRIT_CONFIG = Path(__file__).parent / "criteria.json"

# Fetch local timezone
local_timezone = os.getenv('TZ', 'Asia/Manila')


def load_criteria():
    """Load configuration file for criteria for each defined activity."""
    try:
        with open(CRIT_CONFIG, "r", encoding="utf-8") as f:
            criteria = json.load(f)
        return criteria
    except (json.JSONDecodeError, FileNotFoundError):
        print("Failed to read or find the criteria configuration file.")
        sys.exit(0)


def save_criteria(criteria):
    """Write back configured set of criteria for each activity."""
    try:
        with open(CRIT_CONFIG, "w") as f:
            json.dump(criteria, f, indent=4)
    except Exception as e:
        print(f"Unexpected error occurred: {e}")


def get_coordinates():
    """Prompt the user to choose a coordinate."""
    print("Select a location:")
    for index, name in enumerate(COORDINATE_KEYS, start=1):
        print(f"{index}. {name}")
    
    index = get_index(COORDINATE_KEYS)
    location_name = COORDINATE_KEYS[index]
    lat, lon = VARS[location_name].split(",")
    return location_name, (lat.strip(), lon.strip())


def get_index(items: List[str]) -> int:
    while True:
        try:
            index = int(input("> "))
            if 1 <= index <= len(items):
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


def main_menu():
    print("\nWelcome to Weather Assistant!")
    print("--------------------------------")
    print("1. View 5-Day Forecast")
    print("2. View Current Weather")
    print("3. View Hourly Forecast")
    print("4. Choose a Day for Details")
    print("5. Customize Activity Criteria")
    print("6. Exit")
    return get_index(["5-Day Forecast", "Current Weather", "Hourly Forecast", "Day Details", "Customize Criteria", "Exit"])


def fetch_weather_data(lat, lon, api_key, forecast_type="5-day"):
    """Fetch weather data from OpenWeatherMap API."""
    if forecast_type == "5-day" or forecast_type == "hourly":
        url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    elif forecast_type == "current":
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    else:
        print("Invalid forecast type!")
        sys.exit(1)
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        sys.exit(1)


def parse_weather_data(data, forecast_type="5-day"):
    """Parse weather data into a list of daily, hourly, or current summaries."""
    if forecast_type == "current":
        local_time = datetime.fromtimestamp(data['dt'], tz=ZoneInfo(local_timezone))
        return {
            "date": local_time.strftime('%Y-%m-%d %H:%M:%S'),
            "temp": data['main']['temp'],
            "weather": data['weather'][0]['description'],
            "wind_speed": data['wind']['speed'] * 3.6,
            "rain": data.get('rain', {}).get('1h', 0)
        }

    if forecast_type == "hourly":
        hourly_weather = []
        for forecast in data['list'][:24]:  # Get data for the next 24 hours
            local_time = datetime.fromtimestamp(forecast['dt'], tz=ZoneInfo(local_timezone))
            hourly_weather.append({
                "date": local_time.strftime('%Y-%m-%d %H:%M:%S'),
                "temp": forecast['main']['temp'],
                "weather": forecast['weather'][0]['description'],
                "wind_speed": forecast['wind']['speed'] * 3.6,
                "rain": forecast.get('rain', {}).get('3h', 0)
            })
        return hourly_weather

    daily_weather = []
    for i in range(0, len(data['list']), 8):  # 8 intervals = 1 day
        forecast = data['list'][i]
        local_time = datetime.fromtimestamp(forecast['dt'], tz=ZoneInfo(local_timezone))
        daily_weather.append({
            "date": local_time.strftime('%Y-%m-%d'),
            "temp": forecast['main']['temp'],
            "weather": forecast['weather'][0]['description'],
            "wind_speed": forecast['wind']['speed'] * 3.6,
            "rain": forecast.get('rain', {}).get('3h', 0)
        })
    return daily_weather


def filter_best_days(daily_weather, activity):
    """Filter and rank days with the best weather for an activity."""
    criteria = load_criteria().get(activity, {})
    best_days = [
        day for day in daily_weather
        if criteria["temp_min"] <= day['temp'] <= criteria["temp_max"]
        and day['rain'] <= criteria["rain"]
        and day['wind_speed'] <= criteria["wind_speed"]
    ]
    return sorted(
        best_days,
        key=lambda x: (abs((criteria["temp_min"] + criteria["temp_max"]) / 2 - x['temp']), x['rain'], x['wind_speed'])
    )[:5]


def save_weather_to_file(location_name, daily_weather, activity, best_activity_days):
    """Save the weather forecast and best days to a file."""
    forecast_file = Path.home() / f"storage/shared/Download/weather_{location_name}.txt"
    with open(forecast_file, 'w') as file:
        file.write("Weather Forecast:\n")
        for day in daily_weather:
            file.write(f"Date: {day['date']}, Temp: {day['temp']}°C, Weather: {day['weather'].capitalize()}, "
                       f"Wind: {day['wind_speed']:.2f} km/h, Rain: {day['rain']} mm\n")

        file.write(f"\nBest {activity.capitalize()} Days:\n")
        for day in best_activity_days:
            file.write(f"Date: {day['date']}, Temp: {day['temp']}°C, Weather: {day['weather'].capitalize()}, "
                       f"Wind: {day['wind_speed']:.2f} km/h, Rain: {day['rain']} mm\n")

    print(f"Weather forecast saved to '{forecast_file}'")



def display_grouped_forecast(forecast_data, forecast_type="daily"):
    """
    Display grouped forecast data for daily or hourly types.
    """
    grouped_forecast = defaultdict(list)

    # Group data by date
    for entry in forecast_data:
        date, time = entry['date'].split(" ") if " " in entry['date'] else (entry['date'], None)
        grouped_forecast[date].append({
            "time": time,
            "temp": entry['temp'],
            "weather": entry['weather'].capitalize(),
            "wind_speed": entry['wind_speed'],
            "rain": entry['rain']
        })

    # Display grouped data
    for date, entries in grouped_forecast.items():
        print(f"\nForecast for {date}:")

        # Calculate summary for the date
        avg_temp = sum(e['temp'] for e in entries) / len(entries)
        total_rain = sum(e['rain'] for e in entries)
        max_wind = max(e['wind_speed'] for e in entries)
        
        print(f"  Summary: Avg Temp: {avg_temp:.2f}°C, Total Rain: {total_rain:.2f} mm, Max Wind: {max_wind:.2f} km/h")

        for entry in entries:
            time_info = f"Time: {entry['time']}, " if entry['time'] else ""
            print(f"  {time_info}Temp: {entry['temp']}°C, Weather: {entry['weather']}, "
                  f"Wind: {entry['wind_speed']:.2f} km/h, Rain: {entry['rain']} mm")


def choose_day(daily_weather):
    """Allow the user to select a specific day for detailed weather or hourly forecast."""
    print("\nSelect a day for details:")
    for index, day in enumerate(daily_weather, start=1):
        print(f"{index}. {day['date']} - Temp: {day['temp']}°C, Weather: {day['weather'].capitalize()}")
    
    index = get_index([day['date'] for day in daily_weather])
    selected_day = daily_weather[index]
    print(f"\nDetails for {selected_day['date']}:")
    print(f"Temperature: {selected_day['temp']}°C")
    print(f"Weather: {selected_day['weather'].capitalize()}")
    print(f"Wind Speed: {selected_day['wind_speed']:.2f} km/h")
    print(f"Rain: {selected_day['rain']} mm")
    
    hourly_option = input("\nDo you want to see the hourly forecast for this day? (yes/no): ").strip().lower()
    if hourly_option in ['yes', 'y']:
        return selected_day['date']
    return None


def customize_criteria():
    """Allow users to customize criteria for activities."""
    activity = get_activity()
    criteria = load_criteria()
    print(f"\nCustomize criteria for {activity.capitalize()}:")
    temp_min = int(input("Enter minimum temperature (°C): "))
    temp_max = int(input("Enter maximum temperature (°C): "))
    rain = float(input("Enter maximum rain (mm): "))
    wind_speed = float(input("Enter maximum wind speed (km/h): "))
    criteria[activity] = {"temp_min": temp_min, "temp_max": temp_max, "rain": rain, "wind_speed": wind_speed}
    save_criteria(criteria)
    print(f"Criteria updated for {activity.capitalize()}.")


def main():
    while True:
        choice = main_menu()
        if choice == 0:  # 5-Day Forecast
            activity = get_activity()
            location_name, (lat, lon) = get_coordinates()
            raw_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="5-day")
            daily_weather = parse_weather_data(raw_data)
            best_activity_days = filter_best_days(daily_weather, activity)

            print("\n5-Day Forecast:")
            display_grouped_forecast(daily_weather, forecast_type="daily")

            print("\nBest Days for Activity:")
            display_grouped_forecast(best_activity_days, forecast_type="daily")

            save = input("\nDo you want to save this forecast to a file? (yes/no): ").strip().lower()
            if save in ['yes', 'y']:
                save_weather_to_file(location_name, daily_weather, activity, best_activity_days)
        
        elif choice == 1:  # Current Weather
            location_name, (lat, lon) = get_coordinates()
            raw_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="current")
            current_weather = parse_weather_data(raw_data, forecast_type="current")
            print("\nCurrent Weather:")
            print(f"Date: {current_weather['date']}, Temp: {current_weather['temp']}°C, Weather: {current_weather['weather'].capitalize()}, "
                  f"Wind: {current_weather['wind_speed']:.2f} km/h, Rain: {current_weather['rain']} mm")
        
        elif choice == 2:  # Hourly Forecast
            location_name, (lat, lon) = get_coordinates()
            raw_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="hourly")
            hourly_weather = parse_weather_data(raw_data, forecast_type="hourly")

            print("\nHourly Forecast (Next 24 Hours):")
            display_grouped_forecast(hourly_weather, forecast_type="hourly")
        
        elif choice == 3:  # Day Details
            location_name, (lat, lon) = get_coordinates()
            raw_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="5-day")
            daily_weather = parse_weather_data(raw_data)
            selected_date = choose_day(daily_weather)
            if selected_date:
                hourly_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="hourly")
                hourly_weather = parse_weather_data(hourly_data, forecast_type="hourly")

                print(f"\nHourly Forecast for {selected_date}:")
                display_grouped_forecast(
                    [hour for hour in hourly_weather if hour['date'].startswith(selected_date)],
                    forecast_type="hourly"
                )
        
        elif choice == 4:  # Customize Criteria
            customize_criteria()
        
        elif choice == 5:  # Exit
            print("Goodbye!")
            sys.exit()


if __name__ == "__main__":
    main()