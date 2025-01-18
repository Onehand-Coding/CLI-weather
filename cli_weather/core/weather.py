import logging
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict
from collections import defaultdict
import requests
from ..utils import CLIWeatherException, CacheManager, confirm, get_index, choose_local_path, run_menu
from ..config import API_KEY, LOCAL_TIMEZONE, load_config
from .activity import choose_activity
from .location import get_location, choose_location

logger = logging.getLogger(__file__)

"""Functions that handle weather data proccessing and viewing."""


def fetch_weather_data(lat: float, lon: float, api_key: str, cache: CacheManager, forecast_type: str ="5-day") -> Dict:
    """Fetch weather data from cache  if available,
     else proceed with fetching data using OpenWeatherMap API."""

    cache_key = cache._generate_key(lat, lon, forecast_type)
    cached_data = cache.load(cache_key)
    if cached_data:
        logger.debug(f"Using cached data for {forecast_type}")
        return cached_data
    urls = {
        "5-day": f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric",
        "hourly": f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric",
        "current": f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    }
    try:
        logger.debug(f"Fetching weather data for: '{forecast_type}' forecast from: {urls[forecast_type]}")
        response = requests.get(urls[forecast_type], timeout=10)
        response.raise_for_status()
        logger.debug(f"Data for {forecast_type} fetched successfully.")
        data = response.json()
        cache.save(cache_key, data)
        return data
    except requests.exceptions.Timeout as e:
        logger.error(f"Error fetching weather data, connection timed out: {e}")
        raise CLIWeatherException("Request timed out, Please check your network connection.")
    except requests.exceptions.HTTPError as e:
        logger.error(f"Failed to fetch weather data, HTTP error occurred: {e.response.status_code} {e.response.reason}")
        raise CLIWeatherException("Failed to fetch weather data, HTTP error.")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Failed to fetch weather data, connection error: {e}")
        raise CLIWeatherException("Failed to fetch weather data. Network error, Please check your connection and try again.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather data: {e}")
        raise CLIWeatherException("Failed to fetch weather data, Please try again later.")


def parse_weather_data(data: Dict, forecast_type: str = "5-day") -> List[Dict]:
    """Parse weather data into a list of daily, hourly, or current summaries."""
    logger.debug(f"Parsing weather data for forecast type: {forecast_type}")
    if forecast_type == "current":
        local_time = datetime.fromtimestamp(data['dt'], tz=ZoneInfo(LOCAL_TIMEZONE))
        logger.debug(f"Parsed {forecast_type} weather data successfully...")
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
        logger.debug(f"Parsed {forecast_type} weather data successfully...")
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
    logger.debug(f"Parsed {forecast_type} weather data successfully...")
    return daily_weather


def filter_best_days(daily_weather: List[Dict], activity: str, hourly_weather: List[Dict]) -> List:
    """Filter and rank days with the best weather for an activity."""
    logger.debug(f"Filtering best weather days for {activity}...")
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
            avg_wind = sum(float(w) for w in [min_wind, max_wind]) / 2

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
                    "wind_speed": avg_wind,
                    "hours": hours
                })

        logger.debug(f"Best days for {activity} filtered successfully.")
        return sorted(best_days, key=lambda x: (abs((criteria["temp_min"] + criteria["temp_max"]) / 2 - x["temp"]), x["rain"], x["wind_speed"]))

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

    logger.debug(f"Best days for {activity} filtered successfully.")
    return sorted(best_days, key=lambda x: (abs((criteria["temp_min"] + criteria["temp_max"]) / 2 - x['temp']), x['rain'], x['wind_speed']))[:5]


def display_grouped_forecast(forecast_data: List[Dict], forecast_type: str = "daily") -> None:
    logger.debug(f"Displaying grouped forecast for '{forecast_type}'...")
    grouped_forecast = defaultdict(list)

    for entry in forecast_data:
        date, time = entry['date'].split(" ") if " " in entry['date'] else (entry['date'], None)
        grouped_forecast[date].append({
            "time": time,
            "temp": entry['temp'],
            "weather": entry.get('weather', 'N/A').title(),
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
            print(f"  {time_info}Temp: {entry['temp']}°C, Weather: {entry.get('weather', 'N/A')}, "
                  f"Wind: {entry['wind_speed']:.2f} km/h, Rain: {entry['rain']} mm")


def save_weather_to_file(location_name: str, weather_days: List[Dict], activity: str = None) -> None:
    """Save the weather forecast and best days to a file."""
    logger.debug(f"Saving weather forecast for {location_name}...")
    main_path = Path.home() / "storage/shared"
    prompt = "Choose folder to save weather forecast"
    forecast_file_path = choose_local_path(main_path, prompt)
    forecast_file = forecast_file_path / f"{location_name}_{activity}_weather.txt" if activity is not None else forecast_file_path / f"{location_name}_weather.txt"

    with open(forecast_file, 'w') as file:
        header = f"\nBest {activity.title()} Days:\n" if activity is not None else "Weather Forecast:\n"
        file.write(header)
        for day in weather_days:
            file.write(f"Date: {day['date']}, Temp: {day['temp']:.2f}°C, Weather: {day.get('weather', 'N/A').title()}, "
                       f"Wind: {day['wind_speed']:.2f} km/h, Rain: {day['rain']} mm\n")

    confirm_message = f"Best Weather day(s) for {activity.title()} saved to '{forecast_file}'" if activity is not None else f"Weather forecast saved to '{forecast_file}'"
    logger.debug(confirm_message)
    print(confirm_message)


def view_5day(cache: CacheManager) -> None:
    """Display 5-day weather Forecast for a chosen location."""

    location_name, (lat, lon) = choose_location(task="to view 5-day weather forecast", add_sensitive=True)
    if location_name == "Back":
        return
    logger.debug(f"viewing 5-day weather forecast in {location_name}...")
    raw_data = fetch_weather_data(lat, lon, API_KEY, cache, forecast_type="5-day")
    daily_weather = parse_weather_data(raw_data)

    print("\n5-Day Forecast:")
    display_grouped_forecast(daily_weather, forecast_type="daily")

    if confirm("\nSave Weather Forecast to file?"):
        save_weather_to_file(location_name, daily_weather)


def view_best_activity_day(cache: CacheManager) -> None:
    """View best day(s) for an activity in a chosen location."""
    activity = choose_activity("check")
    if activity == "Back":
        return
    location_name, (lat, lon) = choose_location(task=f"to check best day(s) for {activity}", add_sensitive=True)
    if location_name == "Back":
        return

    # Fetch daily and hourly weather data
    logger.debug(f"viewing best activity days for {activity} in {location_name}...")
    raw_daily_data = fetch_weather_data(lat, lon, API_KEY, cache, forecast_type="5-day")
    daily_weather = parse_weather_data(raw_daily_data)

    raw_hourly_data = fetch_weather_data(lat, lon, API_KEY, cache, forecast_type="hourly")
    hourly_weather = parse_weather_data(raw_hourly_data, forecast_type="hourly")

    # Get the best days for the activity.
    best_activity_days = filter_best_days(daily_weather, activity, hourly_weather)

    # Display the results if theres a good day for the activity.
    if best_activity_days:
        print(f"\nBest Days for {activity.title()}:")
        display_grouped_forecast(best_activity_days, forecast_type="daily")

    # Save to file if the user confirms
    if best_activity_days and confirm("\nSave Weather Forecast to file?"):
        save_weather_to_file(location_name, best_activity_days, activity)
    else:
        print(f"\nThere's no good {activity} weather for now.\n")


def view_current(cache: CacheManager) -> None:
    """View current weather forecast for chosen location."""
    location_name, (lat, lon) = choose_location(task="to view the current weather", add_sensitive=True)
    if location_name == "Back":
        return
    logger.debug(f"Viewing current weather in {location_name}...")
    raw_data = fetch_weather_data(lat, lon, API_KEY, cache, forecast_type="current")
    current_weather = parse_weather_data(raw_data, forecast_type="current")
    print(f"\nCurrent Weather in {location_name}:")
    print(f"Date: {current_weather['date']}, Temp: {current_weather['temp']}°C, Weather: {current_weather['weather'].title()}, "
        f"Wind: {current_weather['wind_speed']:.2f} km/h, Rain: {current_weather['rain']} mm")

def view_hourly(cache: CacheManager) -> None:
    """View hourly forecast for a chosen location."""
    location_name, (lat, lon) = choose_location(task="to view the hourly weather forecast from", add_sensitive=True)
    if location_name == "Back":
        return
    logger.debug(f"viewing hourly weather forecast in {location_name}...")
    raw_data = fetch_weather_data(lat, lon, API_KEY, cache, forecast_type="hourly")
    hourly_weather = parse_weather_data(raw_data, forecast_type="hourly")

    print("\nHourly Forecast (Next 24 Hours):")
    display_grouped_forecast(hourly_weather, forecast_type="hourly")


def view_certain_day(cache: CacheManager) -> None:
    """View forecast for a certain day in chosen location."""
    def choose_day(daily_weather):
        """Allow the user to select a specific day for detailed weather or hourly forecast."""
        print("\nSelect a day for details:")
        for index, day in enumerate(daily_weather, start=1):
            print(f"{index}. {day['date']} - Temp: {day['temp']}°C, Weather: {day['weather'].title()}")

        index = get_index([day['date'] for day in daily_weather])
        return daily_weather[index]

    location_name, (lat, lon) = choose_location(task="to view a certain day\'s weather forecast", add_sensitive=True)
    if location_name == "Back":
        return
    raw_data = fetch_weather_data(lat, lon, API_KEY, cache, forecast_type="5-day")
    daily_weather = parse_weather_data(raw_data)
    selected_day = choose_day(daily_weather)

    logger.debug(f"viewing weather forecast for date: {selected_day} in {location_name}...")
    print(f"\nDetails for {selected_day['date']}:")
    print(f"Temperature: {selected_day['temp']}°C")
    print(f"Weather: {selected_day['weather'].title()}")
    print(f"Wind Speed: {selected_day['wind_speed']:.2f} km/h")
    print(f"Rain: {selected_day['rain']} mm")

    if confirm("\nDo you want to see the hourly forecast for this day?"):
        hourly_data = fetch_weather_data(lat, lon, API_KEY, cache, forecast_type="hourly")
        hourly_weather = parse_weather_data(hourly_data, forecast_type="hourly")

        # Extract date string for filtering
        selected_date = selected_day['date']

        print(f"\nHourly Forecast for {selected_date}:")
        display_grouped_forecast(
            [hour for hour in hourly_weather if hour['date'].startswith(selected_date)],
            forecast_type="hourly"
        )


def view_oncurrent_location(cache: CacheManager) -> None:
    """View different weather forecasts on current location."""
    logger.debug("viewing different weather forecast in current location...")
    def display_oncurrent(forecast_type: str, lat: float, lon: float) -> None:
        """Function to view forcast on current location."""
        raw_data = fetch_weather_data(lat, lon, API_KEY, cache, forecast_type=forecast_type)
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

    def view_best_activity_day_oncurrent(lat: float, lon: float) -> None:
        """View best days for an activity for the current location."""
        logger.debug("viewing best activity day on current location...")
        activity = choose_activity("check")
         # Fetch daily and hourly weather data
        raw_daily_data = fetch_weather_data(lat, lon, API_KEY, cache, forecast_type="5-day")
        daily_weather = parse_weather_data(raw_daily_data)

        raw_hourly_data = fetch_weather_data(lat, lon, API_KEY, cache,  forecast_type="hourly")
        hourly_weather = parse_weather_data(raw_hourly_data, forecast_type="hourly")

        # Get the best days for the activity.
        best_activity_days = filter_best_days(daily_weather, activity, hourly_weather)

        # Display the results if theres a good day for activity.
        if best_activity_days:
            print(f"\nBest Days for {activity.title()} at Current Location:")  # Indicate current location
            display_grouped_forecast(best_activity_days, forecast_type="daily")

        # Save to file if the user confirms. Indicate location in file name.
        if best_activity_days and confirm("\nSave Weather Forecast to file?"):
            save_weather_to_file("Current_Location", best_activity_days, activity)
        else:
            print(f"There's no good {activity} weather for now at the current location.")

    #  Get the current location and run options to execute for this location.
    try:
        address, lat, lon = get_location()
        if any(coord is None for coord in {address, lat, lon}):
            print("Could not determine current location.")
            return
    except CLIWeatherException as e:
        print(e)
        return

    options = [
            {"View Current Weather": lambda: display_oncurrent("current", lat, lon)},
            {"View Hourly Forecast": lambda: display_oncurrent("hourly", lat, lon)},
            {"View 5-Day Forecast": lambda: display_oncurrent("5-day", lat, lon)},
             {"View Best Day(s) for an Activity": lambda: view_best_activity_day_oncurrent(lat, lon)},
            {"Back": None}
        ]

    while True:
        run_menu(options, f"Options for current location {address}:")
        break


def fetch_typhoon_data(api_key: str) -> Dict:
    """Fetch typhoon data from a suitable API."""


def view_typhoon_tracker() -> None:
    """View active typhoons and alerts for the chosen location."""
    print("Not yet implimented.")
