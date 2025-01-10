#!/data/data/com.termux/files/home/coding/cli-weather/.venv/bin/python3
import sys
import json
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime, timezone
from collections import defaultdict
import geopy
import requests
from dotenv import dotenv_values
from geopy.geocoders import Nominatim

# Load environment variables
VARS = dotenv_values()
API_KEY = VARS["OWM_API_KEY"]
LOCAL_TIMEZONE = VARS['TZ']
CONFIG_FILE = Path(__file__).parent / "config.json"
FORECAST_FILE_PATH = Path.home() / "storage/shared/Download"

MAIN_OPTIONS = [
    {"View Current Weather": lambda: view_current()},
    {"View Hourly Forecast": lambda: view_hourly()},
    {"View 5-Day Forecast": lambda: view_5day()},
    {"View Forecast for a Certain Day": lambda: view_certain_day()},
    {"View Best Day(s) for an Activity": lambda: view_best_activity_day()},
    {"View Forecasts in Current Location": lambda : view_oncurrent_location()},
    {"Other Options": lambda: run_menu(OTHER_OPTIONS, "OTHER OPTIONS")},
    {"Exit": None}
]
LOCATION_OPTIONS = [
    {"View locations": lambda : view_locations()},
    {"Add a location": lambda : add_location()},
    {"Add Current Location": lambda : save_current_location()},
    {"Search a location": lambda
        : search_location()
    },
    {"Delete a location": lambda : delete_location()},
    {"Back": None}
]
ACTIVITY_OPTIONS = [
    {"View Activities": lambda: view_activities()},
    {"Add Activity": lambda: add_activity()},
    {"Edit Activity": lambda: edit_activity()},
    {"Delete Activity": lambda: delete_activity()},
    {"Back": None}
]
OTHER_OPTIONS = [
    {"Manage Activities": lambda: run_menu(ACTIVITY_OPTIONS, "Manage Activities")},
    {"Manage Locations": lambda : run_menu(LOCATION_OPTIONS, "Manage Locations")},
    {"Back": None}]
UNITS = {
    "temp_min": "°C",
    "temp_max": "°C",
    "rain": "mm",
    "wind_min": "km/h",
    "wind_max": "km/h",
    "time_range": ""
}


class CLIWeatherException(Exception):
    """Raise for clear and user friendly error message."""


# === Helper functions ===#
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


def get_index(items):
    """Get the index of an item from the given list of items."""
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


def load_config():
    try:
        with open(CONFIG_FILE, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Failed to load configurarion file: {e}")
        return {}   


def save_data(data):
    """Write data to configuration file."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except (json.JSONDecodeError, FileNotFoundError,OSError) as e:
        print(f"Error saving data to configurarion: {e}")
    except Exception as e:
        print(f"Unexpected error occurred: {e}")


def run_menu(options, prompt="", main=False):
    """Run menu to Let user choose and execute options."""
    try:
        while True:
            print(f"\n{prompt}")
            print("--------------------------------")
            for index, option in enumerate(options, start=1):
                print(f"{index}. {list(option)[0]}")
            index = get_index(list(options))
            func = list(options[index].values())[0]
            if main and func is None:
                print("Goodbye!")
                sys.exit()
            if func is None:
                break
            func()
    except KeyboardInterrupt:
        print("Operation cancelled.")
        sys.exit()


# === Activity management functions === #
def get_criteria(activity):
    """Get user criteria for an activity."""
    print(f"\nProvide criteria for {activity}.\n")
    while True:
        try:
            temp_min = int(input("Enter minimum temperature (°C): "))
            temp_max = int(input("Enter maximum temperature (°C): "))
            rain = float(input("Enter maximum rain (mm): "))
            wind_max = float(input("Enter maximum wind speed (km/h): "))

            # Optional minimum wind speed
            wind_min = 0
            if confirm("Does this activity require a minimum wind speed?"):
                wind_min = float(input("Enter minimum wind speed (km/h): "))

            time_range = None
            if confirm("Is this a time-specific activity?"):
                time_start = input("Enter start time (HH:MM, 24-hour format, e.g., 06:00): ").strip()
                time_end = input("Enter end time (HH:MM, 24-hour format, e.g., 12:00): ").strip()
                time_range = [time_start, time_end]

            print(f"""\nNew {activity.title()} Criteria:   
                    Temp: {temp_min}-{temp_max} °C
                    Rain: {rain} mm
                    Wind: {wind_min or 'N/A'}-{wind_max} km/h,
                    Time: {(time_range) if time_range else 'All Day'}\n""")
            
            if confirm("Done?"):
                return {
                    "temp_min": temp_min,
                    "temp_max": temp_max,
                    "rain": rain,
                    "wind_min": wind_min,  # Include minimum wind speed
                    "wind_max": wind_max,  # Rename for clarity
                    "time_range": time_range or ["00:00", "23:59"]
                }
        except ValueError:
            print("Please enter a valid value.")
        except KeyboardInterrupt:
            print("Operation cancelled.")
            sys.exit(0)


def choose_activity(task=None):
    """Get an activity name from configured activities in configuration file."""
    config = load_config()
    activities = config.get("activities", {})
    if not activities:
        print("No activities found. Please add an activity first.")
        return None
    
    prompt = f"Choose an activity to {task}." if task else "Choose an activity."
    print(prompt)
    for i, activity in enumerate(activities.keys(), start=1):
        print(f"{i}. {activity.title()}") # Added index to output

    activity_name = list(activities.keys())[get_index(list(activities))]
    return activity_name


def view_activities():
    """View existing activity-criteria configurations."""
    activities = load_config()["activities"]
    print("\nYour Activities:\n")
    for activity, criteria in activities.items():
        print(f"\t{activity.title()}:")
        for key, value in criteria.items():
            unit = UNITS.get(key, "")
            if isinstance(value, list) and len(value) == 2:
                print(f"\t\t{key.replace('_', ' ').title()}: {value[0]} to {value[1]} {unit}")
            else:
                print(f"\t\t{key.replace('_', ' ').title()}: {value} {unit}")


def add_activity():
    """Add new activity-criteria configuration."""
    activity_name = ""
    while not activity_name:
        activity_name = input("Enter activity name: ").lower().strip()
    criteria = get_criteria(activity_name)
    if confirm("Save activity?"):
        save_activity(activity_name, criteria)
        print(f"\n{activity_name.title()} activity added successfully.")


def edit_activity():
    """Edit existing criteria for an activity."""
    activity_name = choose_activity("edit")
    current_criteria = load_config()["activities"][activity_name]
    print(f"Current criteria for {activity_name.title()}:")
    for key, value in current_criteria.items():
        unit = UNITS.get(key, "")
        if isinstance(value, list) and len(value) == 2:  # Handle range values like time_range
            print(f"  {key.replace('_', ' ').title()}: {value[0]} to {value[1]} {unit}")
        else:
            print(f"  {key.replace('_', ' ').title()}: {value} {unit}")

    new_criteria = get_criteria(activity_name)
    if confirm("Save changes?"):
        save_activity(activity_name, new_criteria)
        print(f"Criteria for {activity_name.title()} updated successfully.")


def delete_activity():
    """Let user remove an existing activity-criteria configuration."""
    activity = choose_activity("remove")
    config = load_config()
    activities= config["activities"]
    if confirm(f"Do you want to remove this activity? {activity}:  {activities[activity]}"):
        del config["activities"][activity]
        save_data(config)
        print(f"\n{activity.title()} activity removed successfully.")


def save_activity(activity_name, criteria):
    """Write configured set of criteria for each activity in configuration file."""
    configuration = load_config()
    configuration.setdefault("activities", {})[activity_name] = criteria
    save_data(configuration)


# === Location management functions === #
def get_location(addr="me"):
    """ Get location by address using geopy."""
    geopy.adapters.BaseAdapter.session = requests.Session()
    try:
        geolocator = Nominatim(user_agent="weather_assistant", timeout=10)
        location = geolocator.geocode(addr)
        if location:
            return location.address, location.latitude, location.longitude, 
        else:
            return None, None, None
    except Exception:
        addr = "your current location" if addr == "me" else addr.title()
        raise CLIWeatherException(f"Failed to locate  {addr}.")


def search_location():
    """Let user search for a location to save."""
    try:
        search_query = input("Enter location to search: ")
        try:
            address, lat, lon = get_location(search_query)
        except CLIWeatherException as e:
            print(f"{e}")
            return

        if all((address, lat, lon)):
            print(f"Found: {address}")
            if confirm("Save this location?"):
                location_name = input("Enter a name for this location: ").strip() or address
                save_location(location_name, f"{lat}, {lon}")  # Save using save_location
                print(f"Location '{location_name}' saved successfully.")
        else:
            print("Location not found.")

    except Exception as e:  # Handle potential geopy exceptions
        print(f"Error searching for location: {e}")


def load_locations(add_current=False, add_sensitive=False):
    """Load combined sensitive, non sensitive, and current locations."""
    non_sensitive_locations = load_config().get("locations", {})
    sensitive_locations = {
        key: value for key, value in VARS.items() 
        if is_valid_location(value)
    }
    locations = {**sensitive_locations, **non_sensitive_locations} if add_sensitive else non_sensitive_locations

    if add_current:
        # Add current location to locations if possible.
        _, lat, lon = get_location()
        if  not any(coord is None for coord in {lat, lon}):
            locations["Current Location"] = f"{str(lat)}, {str(lon)}"
    return locations


def save_location(location_name, coordinate):
    """Write location info into configuration file."""
    configuration = load_config()
    configuration.setdefault("locations", {})[location_name] = coordinate
    save_data(configuration)


def is_valid_location(value):
    """Check if a given value is a valid coordinate for location."""
    try:
        lat, lon = map(float, value.split(","))
        return -90 <= lat <= 90 and -180 <= lon <= 180
    except (ValueError, TypeError):
        return False


def get_location_input():
    """Get location name and coordinate from user."""
    try:
        while True:
            location_name = input("Enter location name: ")
            print("Enter comma separated coordinates Lat/Long (Deg). eg. 1.599, 12.6168")
            coordinate = input("> ")
            if is_valid_location(coordinate) and confirm("Done?"):
                return (location_name, coordinate)
    except KeyboardInterrupt:
        print("Operarion cancelled.")
        sys.exit(0)


def add_location():
    """Add non-sensitive location to configuration file."""
    location_name, coordinate = get_location_input()
    if confirm(f"Save this location?\n {location_name}: {coordinate}"):
        save_location(location_name, coordinate)
        print(f"New location {location_name} saved successfully.")


def save_current_location():
    """Let user save current location."""
    try:
            current_addr, lat, lon = get_location()
    except CLIWeatherException as e:
            print(f"{e}")
            return
    print(f"Current location: {current_addr}:\n\tlatitude: {lat}, longitude: {lon}")
    if confirm("Do you want to rename location address?"):
        current_addr = input("Enter new name for this location: ")
    if confirm("Save this location?"):
        config = load_config()
        config["locations"][current_addr] = f"{str(lat)}, {str(lon)}"
        save_data(config)
        print("Current location saved successfully.")


def view_locations():
    """View non sensitive locations saved by the user."""
    locations = load_locations()
    if not locations:
        print("No locations foud. Please add one first.")
    print("\nYour Locations:\n")
    for location_name, coordinate in locations.items():
        lat, lon = coordinate.split(",")
        print(f"""{location_name.title()}:
            latitude: {lat.strip()}
            longitude: {lon}""")


def delete_location():
    """Let user remove a non sensitive location from configuration."""
    print("\nChoose a location to delete:")
    location_to_delete, _ = choose_location("delete")
    if confirm(f"Are you sure you want to delete '{location_to_delete}'?"):
            config = load_config()
            del config["locations"][location_to_delete]
            save_data(config)
            print(f"\n'{location_to_delete}' deleted successfully.")


def choose_location(task="", add_current=False, add_sensitive=False):
    """Prompt the user to choose a location to be used in getting weather forecast."""
    print(f"Choose a location to {task}:")
    coordinates = load_locations(add_current, add_sensitive)
    for index, name in enumerate(coordinates, start=1):
        print(f"{index}. {name.title()}")
    
    index = get_index(coordinates)
    location_name = list(coordinates.keys())[index]
    lat, lon = coordinates[location_name].split(",")
    return location_name, (lat.strip(), lon.strip())


# == Weather functions == #
def choose_day(daily_weather):
    """Allow the user to select a specific day for detailed weather or hourly forecast."""
    print("\nSelect a day for details:")
    for index, day in enumerate(daily_weather, start=1):
        print(f"{index}. {day['date']} - Temp: {day['temp']}°C, Weather: {day['weather'].title()}")

    index = get_index([day['date'] for day in daily_weather])
    return daily_weather[index]


def fetch_weather_data(lat, lon, api_key, forecast_type="5-day"):
    """Fetch weather data from OpenWeatherMap API."""
    urls = {
        "5-day": f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric",
        "hourly": f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric",
        "current": f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    }
    try:
        response = requests.get(urls[forecast_type])
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        raise CLIWeatherException("Error! Fetching weather data. Please check your network connection.")
    except Exception as e:
        print(f"An unexpected error occurred! {e}")
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


def filter_best_days(daily_weather, activity, hourly_weather):
    """Filter and rank days with the best weather for an activity."""
    criteria = load_config()["activities"].get(activity, {})
    time_range = criteria.get("time_range", ["00:00", "23:59"])

    # Handle time-specific activities
    if time_range != ["00:00", "23:59"]:
        def is_within_time_range(hour_entry):
            time = datetime.strptime(hour_entry["date"].split(" ")[1], "%H:%M:%S").time()
            return datetime.strptime(time_range[0], "%H:%M").time() <= time <= datetime.strptime(time_range[1], "%H:%M").time()

        hourly_within_range = [hour for hour in hourly_weather if is_within_time_range(hour)]
        daily_summary = defaultdict(list)

        for hour in hourly_within_range:
            date = hour["date"].split(" ")[0]
            daily_summary[date].append(hour)

        best_days = []
        for date, hours in daily_summary.items():
            avg_temp = sum(h["temp"] for h in hours) / len(hours)
            total_rain = sum(h["rain"] for h in hours)
            max_wind = max(h["wind_speed"] for h in hours)
            min_wind = min(h["wind_speed"] for h in hours)

            # Check both wind_min and wind_max if applicable
            if (
                criteria["temp_min"] <= avg_temp <= criteria["temp_max"]
                and total_rain <= criteria["rain"]
                and (criteria.get("wind_min", 0) <= min_wind)
                and max_wind <= criteria["wind_max"]
            ):
                best_days.append({
                    "date": date,
                    "temp": avg_temp,
                    "rain": total_rain,
                    "wind_speed": (min_wind, max_wind),
                    "hours": hours
                })

        return sorted(best_days, key=lambda x: (abs((criteria["temp_min"] + criteria["temp_max"]) / 2 - x["temp"]), x["rain"], x["wind_speed"][1]))

    # Handle non-time-specific activities
    best_days = [
        day for day in daily_weather
        if (
            criteria["temp_min"] <= day['temp'] <= criteria["temp_max"]
            and day['rain'] <= criteria["rain"]
            and (criteria.get("wind_min", 0) <= day['wind_speed'])
            and day['wind_speed'] <= criteria["wind_max"]
        )
    ]

    return sorted(best_days, key=lambda x: (abs((criteria["temp_min"] + criteria["temp_max"]) / 2 - x['temp']), x['rain'], x['wind_speed']))[:5]


def display_grouped_forecast(forecast_data, forecast_type="daily"):
    grouped_forecast = defaultdict(list)

    for entry in forecast_data:
        date, time = entry['date'].split(" ") if " " in entry['date'] else (entry['date'], None)
        grouped_forecast[date].append({
            "time": time,
            "temp": entry['temp'],
            "weather": entry['weather'].title(),
            "wind_speed": entry['wind_speed'],
            "rain": entry['rain']
        })

    for date, entries in grouped_forecast.items():
        print(f"\nForecast for {date}:")

        avg_temp = sum(e['temp'] for e in entries) / len(entries)
        total_rain = sum(e['rain'] for e in entries)
        max_wind = max(e['wind_speed'] for e in entries)
        min_wind = min(e['wind_speed'] for e in entries)

        print(f"  Summary: Avg Temp: {avg_temp:.2f}°C, Total Rain: {total_rain:.2f} mm, Wind Range: {min_wind:.2f}-{max_wind:.2f} km/h")
        
        for entry in entries:
            time_info = f"Time: {entry['time']}, " if entry['time'] else ""
            print(f"  {time_info}Temp: {entry['temp']}°C, Weather: {entry['weather']}, "
                  f"Wind: {entry['wind_speed']:.2f} km/h, Rain: {entry['rain']} mm")


def save_weather_to_file(location_name, weather_days, activity=None):
    """Save the weather forecast and best days to a file."""
    forecast_file = FORECAST_FILE_PATH / f"{location_name}_weather.txt" if activity is None else FORECAST_FILE_PATH / f"{location_name}_{activity}_weather.txt"

    with open(forecast_file, 'w') as file:
        header = f"\nBest {activity.title()} Days:\n" if activity else "Weather Forecast:\n"
        file.write(header)
        for day in weather_days:
            file.write(f"Date: {day['date']}, Temp: {day['temp']}°C, Weather: {day['weather'].title()}, "
                       f"Wind: {day['wind_speed']:.2f} km/h, Rain: {day['rain']} mm\n")
    
    confirm_message = f"Best Weather day(s) for {activity.title()} saved to '{forecast_file}'" if activity else f"Weather forecast saved to '{forecast_file}'"
    print(confirm_message)


def view_5day():
    """Display 5-day weather Forecast for a chosen location."""
    location_name, (lat, lon) = choose_location("view the 5-day weather forecast", add_sensitive=True)
    try:
        raw_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="5-day")
    except CLIWeatherException as e:
        print(e)
        return
    daily_weather = parse_weather_data(raw_data)

    print("\n5-Day Forecast:")
    display_grouped_forecast(daily_weather, forecast_type="daily")
    
    if confirm("\nSave Weather Forecast to file?"):
        save_weather_to_file(location_name, daily_weather)


def view_best_activity_day():
    """View best day(s) for an activity in a chosen location."""
    activity = choose_activity("check")
    location_name, (lat, lon) = choose_location(f"check best day(s) for {activity}", add_sensitive=True)
    
    # Fetch daily and hourly weather data
    try:
        raw_daily_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="5-day")
        daily_weather = parse_weather_data(raw_daily_data)
        
        raw_hourly_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="hourly")
        hourly_weather = parse_weather_data(raw_hourly_data, forecast_type="hourly")
    except CLIWeatherException as e:
        print(e)
        return
    
    # Get the best days for the activity.
    best_activity_days = filter_best_days(daily_weather, activity, hourly_weather)
    
    # Display the results if theres a good day for activity.
    if best_activity_days:
        print(f"\nBest Days for {activity.title()}:")
        display_grouped_forecast(best_activity_days, forecast_type="daily")
    
    # Save to file if the user confirms
    if best_activity_days and confirm("\nSave Weather Forecast to file?"):
        save_weather_to_file(location_name, best_activity_days, activity, best_activity_days=True)
    else:
        print(f"There's no good {activity} weather for now.")


def view_current():
    """View current weather forecast for chosen location."""
    location_name, (lat, lon) = choose_location("view the current weather", add_sensitive=True)
    try:
        raw_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="current")
    except CLIWeatherException as e:
        print(e)
        return
    current_weather = parse_weather_data(raw_data, forecast_type="current")
    print("\nCurrent Weather:")
    print(f"Date: {current_weather['date']}, Temp: {current_weather['temp']}°C, Weather: {current_weather['weather'].title()}, "
        f"Wind: {current_weather['wind_speed']:.2f} km/h, Rain: {current_weather['rain']} mm")


def view_hourly():
    """View hourly forecast for a chosen location."""
    location_name, (lat, lon) = choose_location("view the hourly weather forecast from", add_sensitive=True)
    try:
        raw_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="hourly")
        hourly_weather = parse_weather_data(raw_data, forecast_type="hourly")
    except CLIWeatherException as e:
        print(e)
        return

    print("\nHourly Forecast (Next 24 Hours):")
    display_grouped_forecast(hourly_weather, forecast_type="hourly")


def view_certain_day():
    """View forecast for a certain day for the chosen location."""
    location_name, (lat, lon) = choose_location("view weather forecast for a certain day", add_sensitive=True)
    try:
        raw_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="5-day")
    except CLIWeatherException as e:
        print(e)
        return
    daily_weather = parse_weather_data(raw_data)
    selected_day = choose_day(daily_weather)
    
    print(f"\nDetails for {selected_day['date']}:")
    print(f"Temperature: {selected_day['temp']}°C")
    print(f"Weather: {selected_day['weather'].title()}")
    print(f"Wind Speed: {selected_day['wind_speed']:.2f} km/h")
    print(f"Rain: {selected_day['rain']} mm")
    
    if confirm("\nDo you want to see the hourly forecast for this day?"):
        hourly_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="hourly")
        hourly_weather = parse_weather_data(hourly_data, forecast_type="hourly")

        # Extract date string for filtering
        selected_date = selected_day['date']

        print(f"\nHourly Forecast for {selected_date}:")
        display_grouped_forecast(
            [hour for hour in hourly_weather if hour['date'].startswith(selected_date)],
            forecast_type="hourly"
        )


def view_oncurrent_location():
    """View different weather forecasts on current location."""
    def view_weather_for_coords(forecast_type, lat, lon):
        """Function to view forcast on current location."""
        raw_data = fetch_weather_data(lat, lon, API_KEY, forecast_type=forecast_type)
        if forecast_type == "current":
            weather_data = parse_weather_data(raw_data, forecast_type="current")
            print("\nCurrent Weather at Current Location:") # Indicate Current Location
            print(f"Date: {weather_data['date']}, Temp: {weather_data['temp']}°C, Weather: {weather_data['weather'].title()}, "
            f"Wind: {weather_data['wind_speed']:.2f} km/h, Rain: {weather_data['rain']} mm")

        elif forecast_type == "hourly":
            weather_data = parse_weather_data(raw_data, forecast_type="hourly")
            print("\nHourly Forecast at Current Location (Next 24 Hours):")  # Indicate current Location
            display_grouped_forecast(weather_data, forecast_type="hourly")
        else: #5-Day
            weather_data = parse_weather_data(raw_data)
            print("\n5-Day Forecast at Current Location:")  # Indicate current Location
            display_grouped_forecast(weather_data, forecast_type="daily")

        if confirm("\nSave Weather Forecast to file?"):
            location_name = f"location:{str(lat)},{str(lon)}"
            save_weather_to_file(location_name, weather_data)

    def view_best_activity_day_for_coords(lat, lon):
        """View best days for an activity for the current location."""
        activity = choose_activity("check")
         # Fetch daily and hourly weather data
        raw_daily_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="5-day")
        daily_weather = parse_weather_data(raw_daily_data)
        
        raw_hourly_data = fetch_weather_data(lat, lon, API_KEY, forecast_type="hourly")
        hourly_weather = parse_weather_data(raw_hourly_data, forecast_type="hourly")
        
        # Get the best days for the activity.
        best_activity_days = filter_best_days(daily_weather, activity, hourly_weather)
        
        # Display the results if theres a good day for activity.
        if best_activity_days:
            print(f"\nBest Days for {activity.title()} at Current Location:")  # Indicate current location
            display_grouped_forecast(best_activity_days, forecast_type="daily")
        
        # Save to file if the user confirms. Indicate location in file name.
        if best_activity_days and confirm("\nSave Weather Forecast to file?"):
            save_weather_to_file(f"Current_Location_{activity}", best_activity_days, activity, best_activity_days=True)
        else:
            print(f"There's no good {activity} weather for now at the current location.")

    #  Get the current location and run options to execute for this location.
    try:
        _, lat, lon = get_location()
        if any(coord is None for coord in {lat, lon}):
            print("Could not determine current location.")
            return
    except CLIWeatherException as e:
        print(e)
        return
    
    options = [
            {"View Current Weather": lambda: view_weather_for_coords("current", lat, lon)},
            {"View Hourly Forecast": lambda: view_weather_for_coords("hourly", lat, lon)},
            {"View 5-Day Forecast": lambda: view_weather_for_coords("5-day", lat, lon)},
             {"View Best Day(s) for an Activity": lambda: view_best_activity_day_for_coords(lat, lon)},
            {"Back": None}
        ]

    while True:
        print("\nCurrent Location Weather Options:")
        run_menu(options, "Choose an option:")
        #if options[get_index(options)].get("Back") is None: # Check for the "Back" option
        break


def main():
    print("\nWelcome to CLI Weather Assistant!")
    while True:
        run_menu(MAIN_OPTIONS, "MAIN OPTIONS", main=True)


if __name__ == "__main__":
    main()