#!/data/data/com.termux/files/home/coding/cli-weather/.venv/bin/python3
import os
import sys
import json
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime, timezone
from typing import List
from collections import defaultdict
import requests
from dotenv import dotenv_values

# Load environment variables
VARS = dotenv_values()
API_KEY = VARS["API_KEY"]
LOCAL_TIMEZONE = VARS['TZ']
COORDINATE_KEYS = [key for key in VARS if key not in {"API_KEY", "TZ"}]
CONFIG_FILE = Path(__file__).parent / "activity-criteria.json"

MAIN_OPTIONS =[
    {"View 5-Day Forecast": lambda : view_5day()},
    {"View Best day/s for an Activity": lambda : view_best_activity_day()},
    {"View Current Weather": lambda : view_current()},
    {"View Hourly Forecast": lambda : view_hourly()},
    {"View Forecast for a Certain day": lambda: view_certain_day()},
    {"Manage Activities": lambda : manage_activities()},
    {"Exit": None}
]
CUSTOMIZE_CRITERIA_OPTIONS=[
    {"View Activities": lambda : view_activity_config()},
    {"Add Activity": lambda : add_activity()},
    {"Edit Activity": lambda : edit_activity()},
    {"Delete Activity": lambda : delete_activity()},
    {"Back to Main Menu": None}
]


def confirm(prompt):
    """Prompt user for confirmation."""
    choice = ""
    try:
        while choice not in {"y", "n", "yes", "no"}:
            choice = input(f"{prompt} (Y/n): ").lower()
        return choice in {"y", "yes"}
    except KeyboardInterrupt:
        print("Operation cancelled by user.")
        sys.exit(0)


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
    activities = sorted(load_activities().keys())
    for i, activity in enumerate(activities, start=1):
        print(i, activity.capitalize())
    return activities[get_index(activities)]


def get_criteria(activity):
    """Get criteria for an activity."""
    print(f"Enter value for each criteria for {activity} activity.")
    while True:
        try:
            temp_min = int(input("Enter minimum temperature (°C): "))
            temp_max = int(input("Enter maximum temperature (°C): "))
            rain = float(input("Enter maximum rain (mm): "))
            wind_speed = float(input("Enter maximum wind speed (km/h): "))
            print(f"""{activity} Criterias:   
                "temp_min": {temp_min},
                "temp_max": {temp_max},
                "rain": {rain},
                "wind_speed": {wind_speed}""")
            if confirm("Done?"):
                return {"temp_min": temp_min, "temp_max": temp_max, "rain": rain, "wind_speed": wind_speed}
        except ValueError:
            print("Please enter a valid value.")
        except KeyboardInterrupt:
            print("Operation cancelled.")
            sys.exit(0)


def view_activity_config():
    """View existing activity-criteria configurations."""
    activities = load_activities()
    print("Existing activity-criteria configurations:\n")
    for activity, criteria in activities.items():
        print(f"{activity.capitalize()}:")
        for k, v in criteria.items():
            print(f"\t{k}: {v}")


def add_activity():
    """Add new activity-criteria configuration."""
    print("Adding new activity-criteria configuration...")
    activity = ""
    while not activity:
        activity = input("Enter activity name: ").lower().strip()
    criteria = get_criteria(activity)
    if confirm("Save activity?"):
        activities = load_activities()
        activities[activity] = criteria
        save_activity(activities)
        print(f"{activity.capitalize()} activity added successfully.")


def edit_activity():
    """Edit existing criteria for an activity."""
    activity = get_activity()
    activities = load_activities()
    print(f"\nEditing criteria for {activity.capitalize()}...")
    print(f"Current criteria for {activity.capitalize()}: {activities[activity]}\n")
    activities[activity] = get_criteria(activity)
    print(f"New criterias for {activity}:\n {activities.get(activity)}")
    if confirm("Save changes?"):
        save_activity(activities)
        print(f"Criterias for {activity.capitalize()} updated successfully.")


def delete_activity():
    """Let user remove an existing activity-criteria configuration."""
    print("Choose activity to remove.")
    activity = get_activity()
    activities = load_activities()
    if confirm(f"Do you want to remove this activity? {activity}:  {activities[activity]}"):
        del activities[activity]
        save_activity(activities)
        print(f"{activity.capitalize()} activity removed from activity-criteria configuration successfully.")


def load_activities():
    """Load configuration file for activities."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            activities = json.load(f)
        return activities
    except (json.JSONDecodeError, FileNotFoundError):
        print("Failed to read or find the criteria configuration file.")
        sys.exit(0)


def save_activity(activities):
    """Write back configured set of criteria for each activity."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(activities, f, indent=4)
    except Exception as e:
        print(f"Unexpected error occurred: {e}")


def manage_activities():
    """Allow users to customize criteria for activities."""
    try:
        while True:
            print("\nManage Activities.")
            print("--------------------------------")
            for index, option in enumerate(CUSTOMIZE_CRITERIA_OPTIONS, start=1):
                print(f"{index}. {list(option)[0]}")
            index = get_index(list(CUSTOMIZE_CRITERIA_OPTIONS))
            activity_func = list(CUSTOMIZE_CRITERIA_OPTIONS[index].values())[0]
            if activity_func is None:
                break
            activity_func()
    except KeyboardInterrupt:
        print("Operation cancelled.")
        sys.exit()


def main_menu():
    """Display the main options and let user choose one to execute the corresponding function."""
    print("\nMAIN OPTIONS")
    print("--------------------------------")
    for index, action in enumerate(MAIN_OPTIONS, start=1):
        print(f"{index}. {list(action)[0]}")

    return list(MAIN_OPTIONS[get_index(MAIN_OPTIONS)].values())[0]


def view_5day():
    """Display 5-day weather Forecast for a chosen location."""
    location_name, (lat, lon) = get_coordinates()
    raw_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="5-day")
    daily_weather = parse_weather_data(raw_data)

    print("\n5-Day Forecast:")
    display_grouped_forecast(daily_weather, forecast_type="daily")
    
    if confirm("\nSave Weather Forecast to file?"):
        save_weather_to_file(location_name, daily_weather)


def view_best_activity_day():
    """View best day/s for an activity in a chosen location."""
    activity = get_activity()
    location_name, (lat, lon) = get_coordinates()
    raw_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="5-day")
    daily_weather = parse_weather_data(raw_data)
    best_activity_days = filter_best_days(daily_weather, activity)

    print(f"\nBest Days for {activity.capitalize()}:")
    display_grouped_forecast(best_activity_days, forecast_type="daily")
    
    if confirm("\nSave Weather Forecast to file?"):
        save_weather_to_file(location_name, best_activity_days, activity, best_activity_days=True)


def view_current():
    """View current weather forecast for chosen location."""
    location_name, (lat, lon) = get_coordinates()
    raw_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="current")
    current_weather = parse_weather_data(raw_data, forecast_type="current")
    print("\nCurrent Weather:")
    print(f"Date: {current_weather['date']}, Temp: {current_weather['temp']}°C, Weather: {current_weather['weather'].capitalize()}, "
        f"Wind: {current_weather['wind_speed']:.2f} km/h, Rain: {current_weather['rain']} mm")


def view_hourly():
    """View hourly forecast for a chosen location."""
    location_name, (lat, lon) = get_coordinates()
    raw_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="hourly")
    hourly_weather = parse_weather_data(raw_data, forecast_type="hourly")

    print("\nHourly Forecast (Next 24 Hours):")
    display_grouped_forecast(hourly_weather, forecast_type="hourly")


def view_certain_day():
    """View forecast for a certain day for the chosen location."""
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


def get_coordinates():
    """Prompt the user to choose a coordinate."""
    print("Select a location:")
    for index, name in enumerate(COORDINATE_KEYS, start=1):
        print(f"{index}. {name}")
    
    index = get_index(COORDINATE_KEYS)
    location_name = COORDINATE_KEYS[index]
    lat, lon = VARS[location_name].split(",")
    return location_name, (lat.strip(), lon.strip())


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
    
    if confirm("\nDo you want to see the hourly forecast for this day?"):
        return selected_day['date']
    return None


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
        local_time = datetime.fromtimestamp(data['dt'], tz=ZoneInfo(LOCAL_TIMEZONE))
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
            local_time = datetime.fromtimestamp(forecast['dt'], tz=ZoneInfo(LOCAL_TIMEZONE))
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
        local_time = datetime.fromtimestamp(forecast['dt'], tz=ZoneInfo(LOCAL_TIMEZONE))
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
    criteria = load_activities().get(activity, {})
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


def save_weather_to_file(location_name, weather_days, activity=None, best_activity_days=False):
    """Save the weather forecast and best days to a file."""
    forecast_file = Path.home() / f"storage/shared/Download/{location_name}_weather.txt"
    with open(forecast_file, 'w') as file:
        header = f"\nBest {activity.capitalize()} Days:\n" if activity is not None and best_activity_days else "Weather Forecast:\n"
        file.write(header)
        for day in weather_days:
            file.write(f"Date: {day['date']}, Temp: {day['temp']}°C, Weather: {day['weather'].capitalize()}, "
                       f"Wind: {day['wind_speed']:.2f} km/h, Rain: {day['rain']} mm\n")

    print(f"Weather forecast saved to '{forecast_file}'")


def main():
    print("\nWelcome to CLI Weather Assistant!")
    while True:
        choice = main_menu()
        if choice is None:  # Exit
            print("Goodbye!")
            sys.exit()
        choice()


if __name__ == "__main__":
    main()