"""Weather data handling functions."""

import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Tuple
from collections import defaultdict

import requests

from .utils import (
    CLIWeatherException,
    CacheManager,
    confirm,
    get_index,
    choose_local_path,
    run_menu,
)
from .config import API_KEY, LOCAL_TIMEZONE, load_config
from .activity import choose_activity
from .location import get_location, choose_location

logger = logging.getLogger(__file__)


def fetch_weather_data(
    lat: float,
    lon: float,
    api_key: str,
    cache: CacheManager,
    forecast_type: str = "5-day",
) -> Dict:
    """Fetches weather data from API or cache."""

    cache_key = cache._generate_key(lat, lon, forecast_type)
    cached_data = cache.load(cache_key)
    if cached_data:
        logger.debug(f"Using cached data for {forecast_type}")
        return cached_data
    urls = {
        "5-day": f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric",
        "hourly": f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric",
        "current": f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric",
    }
    try:
        logger.debug(
            f"Fetching weather data for: '{forecast_type}' forecast from: {urls[forecast_type]}"
        )
        response = requests.get(urls[forecast_type], timeout=10)
        response.raise_for_status()
        logger.debug(f"Data for {forecast_type} fetched successfully.")
        data = response.json()
        cache.save(cache_key, data)
        return data
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.error(
                f"Failed to fetch weather data. Location not found: {lat}, {lon}"
            )
            raise CLIWeatherException(
                "Failed to fetch weather data. Location not found!"
            )
        elif e.response.status_code == 401:
            logger.error(f"Failed to fetch weather data. Invalid API key: {api_key}")
            raise CLIWeatherException(
                f"Failed to fetch weather data. Invalid API key: {api_key}"
            )
        else:
            logger.error(
                f"Failed to fetch weather data, HTTP error occurred: {e.response.status_code} {e.response.reason}"
            )
            raise CLIWeatherException(
                f"Failed to fetch weather data, {e.response.reason}."
            )
    except requests.exceptions.Timeout as e:
        logger.error(f"Error fetching weather data, connection timed out: {e}")
        raise CLIWeatherException(
            "Request timed out, Please check your network connection."
        )
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Failed to fetch weather data, connection error: {e}")
        raise CLIWeatherException(
            "Network error, Please check your connection and try again."
        )
    except requests.exceptions.RequestException as e:
        logger.exception(f"Error fetching weather data: {e}")
        raise CLIWeatherException(
            "Failed to fetch weather data, Unexpected request error occurred."
        )


def parse_weather_data(data: Dict, forecast_type: str = "5-day") -> List[Dict] | Dict:
    """Parse weather data into a list of daily, hourly, or current summaries."""
    logger.debug(f"Parsing weather data for forecast type: {forecast_type}")
    if forecast_type == "current":
        local_time = datetime.fromtimestamp(data["dt"], tz=ZoneInfo(LOCAL_TIMEZONE))
        logger.debug(f"Parsed {forecast_type} weather data successfully...")
        return {
            "date": local_time.strftime("%Y-%m-%d %H:%M:%S"),
            "temp": data["main"]["temp"],
            "weather": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"] * 3.6,
            "rain": data.get("rain", {}).get("1h", 0),
        }

    if forecast_type == "hourly":
        hourly_weather = []
        for forecast in data["list"][:24]:  # Get data for the next 24 hours
            local_time = datetime.fromtimestamp(
                forecast["dt"], tz=ZoneInfo(LOCAL_TIMEZONE)
            )
            hourly_weather.append(
                {
                    "date": local_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "temp": forecast["main"]["temp"],
                    "weather": forecast["weather"][0]["description"],
                    "wind_speed": forecast["wind"]["speed"] * 3.6,
                    "rain": forecast.get("rain", {}).get("3h", 0),
                }
            )
        logger.debug(f"Parsed {forecast_type} weather data successfully...")
        return hourly_weather

    daily_weather = []
    for i in range(0, len(data["list"]), 8):  # 8 intervals = 1 day
        forecast = data["list"][i]
        local_time = datetime.fromtimestamp(forecast["dt"], tz=ZoneInfo(LOCAL_TIMEZONE))
        daily_weather.append(
            {
                "date": local_time.strftime("%Y-%m-%d"),
                "temp": forecast["main"]["temp"],
                "weather": forecast["weather"][0]["description"],
                "wind_speed": forecast["wind"]["speed"] * 3.6,
                "rain": forecast.get("rain", {}).get("3h", 0),
            }
        )
    logger.debug(f"Parsed {forecast_type} weather data successfully...")
    return daily_weather


def filter_best_days(
    daily_weather: List[Dict], activity: str, hourly_weather: List[Dict]
) -> List:
    """Filter best days for specific activity."""
    logger.debug(f"Filtering best weather days for {activity}...")
    criteria = load_config()["activities"].get(activity, {})
    time_range = criteria.get("time_range", ["00:00", "23:59"])

    # Handle time-specific activities
    if time_range != ["00:00", "23:59"]:

        def is_within_time_range(hour_entry):
            time = datetime.strptime(
                hour_entry["date"].split(" ")[1], "%H:%M:%S"
            ).time()
            return (
                datetime.strptime(time_range[0], "%H:%M").time()
                <= time
                <= datetime.strptime(time_range[1], "%H:%M").time()
            )

        hourly_within_range = [
            hour for hour in hourly_weather if is_within_time_range(hour)
        ]
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
                best_days.append(
                    {
                        "date": date,
                        "temp": avg_temp,
                        "rain": total_rain,
                        "wind_speed": avg_wind,
                        "hours": hours,
                    }
                )

        logger.debug(f"Best days for {activity} filtered successfully.")
        return sorted(
            best_days,
            key=lambda x: (
                abs((criteria["temp_min"] + criteria["temp_max"]) / 2 - x["temp"]),
                x["rain"],
                x["wind_speed"],
            ),
        )

    # Handle non-time-specific activities
    best_days = [
        day
        for day in daily_weather
        if (
            criteria["temp_min"] <= day["temp"] <= criteria["temp_max"]
            and day["rain"] <= criteria["rain"]
            and (criteria.get("wind_min", 0) <= day["wind_speed"])
            and day["wind_speed"] <= criteria["wind_max"]
        )
    ]

    logger.debug(f"Best days for {activity} filtered successfully.")
    return sorted(
        best_days,
        key=lambda x: (
            abs((criteria["temp_min"] + criteria["temp_max"]) / 2 - x["temp"]),
            x["rain"],
            x["wind_speed"],
        ),
    )[:5]


def display_grouped_forecast(
    forecast_data: List[Dict], forecast_type: str = "daily"
) -> None:
    """Displays weather forecasts grouped by date."""
    logger.debug(f"Displaying grouped forecast for '{forecast_type}'...")
    grouped_forecast = defaultdict(list)

    for entry in forecast_data:
        date, time = (
            entry["date"].split(" ") if " " in entry["date"] else (entry["date"], None)
        )
        grouped_forecast[date].append(
            {
                "time": time,
                "temp": entry["temp"],
                "weather": entry.get("weather", "N/A").title(),
                "wind_speed": entry["wind_speed"],
                "rain": entry["rain"],
            }
        )

    for date, entries in grouped_forecast.items():
        print(f"\nForecast for {date}:")

        avg_temp = sum(e["temp"] for e in entries) / len(entries)
        total_rain = sum(e["rain"] for e in entries)
        max_wind = max(e["wind_speed"] for e in entries)
        min_wind = min(e["wind_speed"] for e in entries)

        print(
            f"  Summary: Avg Temp: {avg_temp:.2f}°C, Total Rain: {total_rain:.2f} mm, Wind Range: {min_wind:.2f}-{max_wind:.2f} km/h"
        )

        for entry in entries:
            time_info = f"Time: {entry['time']}, " if entry["time"] else ""
            print(
                f"  {time_info}Temp: {entry['temp']:.2f}°C, Weather: {entry.get('weather', 'N/A')}, "
                f"Wind: {entry['wind_speed']:.2f} km/h, Rain: {entry['rain']} mm"
            )


def save_weather_to_file(
    location_name: str, weather_days: List[Dict], activity: str = ""
) -> None:
    """Saves weather forecast to a file."""
    logger.debug(f"Saving weather forecast for {location_name}...")
    forecast_file_path = choose_local_path()
    forecast_file = (
        forecast_file_path / f"{location_name}_{activity}_weather.txt"
        if activity
        else forecast_file_path / f"{location_name}_weather.txt"
    )

    with open(forecast_file, "w") as file:
        header = (
            f"\nBest {activity.title()} Days:\n" if activity else "Weather Forecast:\n"
        )
        file.write(header)
        for day in weather_days:
            file.write(
                f"Date: {day['date']}, Temp: {day['temp']:.2f}°C, Weather: {day.get('weather', 'N/A').title()}, "
                f"Wind: {day['wind_speed']:.2f} km/h, Rain: {day['rain']} mm\n"
            )

    confirm_message = (
        f"Best Weather day(s) for {activity.title()} saved to '{forecast_file}'"
        if activity
        else f"Weather forecast saved to '{forecast_file}'"
    )
    logger.debug(confirm_message)
    print(confirm_message)


def get_location_for_weather(task: str) -> Tuple[str, float, float]:
    """
    Helper function to get location information for weather-related tasks.

    Args:
        task: Description of the task for which location is needed

    Returns:
        Tuple of (location_name, latitude, longitude)

    Raises:
        CLIWeatherException: If location selection fails
    """
    location_name, (lat, lon) = choose_location(
        task=task, add_sensitive=True, add_search=True, add_current=True
    )
    if location_name == "Back":
        raise CLIWeatherException("Operation cancelled by user")
    if location_name == "Current location":
        location_name, lat, lon = get_location()
    if location_name == "Search location":
        print("Enter the address to search.")
        address = input("> ").strip()
        location_name, lat, lon = get_location(address)
    return location_name, lat, lon


def view_5day(cache: CacheManager) -> None:
    """Displays 5-day weather Forecast for a chosen location."""
    try:
        location_name, lat, lon = get_location_for_weather(
            "to view 5-day weather forecast"
        )
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return

    logger.debug(f"viewing 5-day weather forecast in {location_name}...")
    try:
        raw_data = fetch_weather_data(lat, lon, API_KEY, cache, forecast_type="5-day")
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return
    daily_weather = parse_weather_data(raw_data)

    print("\n5-Day Forecast:")
    display_grouped_forecast(daily_weather, forecast_type="daily")

    if confirm("\nSave Weather Forecast to file?"):
        save_weather_to_file(location_name, daily_weather)


def view_best_activity_day(cache: CacheManager) -> None:
    """Displays the best days for a chosen activity."""
    activity = choose_activity("check")
    if not activity or activity == "Back":
        return

    try:
        location_name, lat, lon = get_location_for_weather(
            "to check best days for activity"
        )
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return

    # Fetch daily and hourly weather data
    logger.debug(f"viewing best activity days for {activity} in {location_name}...")
    try:
        raw_daily_data = fetch_weather_data(
            lat, lon, API_KEY, cache, forecast_type="5-day"
        )
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return
    daily_weather = parse_weather_data(raw_daily_data)

    try:
        raw_hourly_data = fetch_weather_data(
            lat, lon, API_KEY, cache, forecast_type="hourly"
        )
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return
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
    """Displays current weather condition for chosen location."""
    try:
        location_name, lat, lon = get_location_for_weather("to view current weather")
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return

    logger.debug(f"Viewing current weather in {location_name}...")
    try:
        raw_data = fetch_weather_data(lat, lon, API_KEY, cache, forecast_type="current")
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return
    current_weather = parse_weather_data(raw_data, forecast_type="current")
    print(f"\nCurrent Weather in {location_name}:")
    print(
        f"Date: {current_weather['date']}, Temp: {current_weather['temp']}°C, Weather: {current_weather['weather'].title()}, "
        f"Wind: {current_weather['wind_speed']:.2f} km/h, Rain: {current_weather['rain']} mm"
    )


def view_hourly(cache: CacheManager) -> None:
    """Displays the hourly forecast for a chosen location."""
    try:
        location_name, lat, lon = get_location_for_weather("to view hourly forecast")
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return

    logger.debug(f"viewing hourly weather forecast in {location_name}...")
    try:
        raw_data = fetch_weather_data(lat, lon, API_KEY, cache, forecast_type="hourly")
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return
    hourly_weather = parse_weather_data(raw_data, forecast_type="hourly")

    print("\nHourly Forecast (Next 24 Hours):")
    display_grouped_forecast(hourly_weather, forecast_type="hourly")


def view_certain_day(cache: CacheManager) -> None:
    """Displays forecast for a certain day in chosen location."""

    def choose_day(daily_weather):
        """Allow the user to select a specific day for detailed weather or hourly forecast."""
        print("\nSelect a day for details:")
        for index, day in enumerate(daily_weather, start=1):
            print(
                f"{index}. {day['date']} - Temp: {day['temp']}°C, Weather: {day['weather'].title()}"
            )

        index = get_index([day["date"] for day in daily_weather])
        return daily_weather[index]

    try:
        location_name, lat, lon = get_location_for_weather(
            "to view forecast for a specific day"
        )
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return

    try:
        raw_data = fetch_weather_data(lat, lon, API_KEY, cache, forecast_type="5-day")
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return
    daily_weather = parse_weather_data(raw_data)
    selected_day = choose_day(daily_weather)

    logger.debug(
        f"viewing weather forecast for date: {selected_day} in {location_name}..."
    )
    print(f"\nDetails for {selected_day['date']}:")
    print(f"Temperature: {selected_day['temp']}°C")
    print(f"Weather: {selected_day['weather'].title()}")
    print(f"Wind Speed: {selected_day['wind_speed']:.2f} km/h")
    print(f"Rain: {selected_day['rain']} mm")

    if confirm("\nDo you want to see the hourly forecast for this day?"):
        hourly_data = fetch_weather_data(
            lat, lon, API_KEY, cache, forecast_type="hourly"
        )
        hourly_weather = parse_weather_data(hourly_data, forecast_type="hourly")

        # Extract date string for filtering
        selected_date = selected_day["date"]

        print(f"\nHourly Forecast for {selected_date}:")
        display_grouped_forecast(
            [hour for hour in hourly_weather if hour["date"].startswith(selected_date)],
            forecast_type="hourly",
        )


def fetch_typhoon_data(api_key: str, lat: float, lon: float) -> Dict:
    """
    Fetch typhoon data and weather alerts from OpenWeatherMap API.

    Args:
        api_key: OpenWeatherMap API key
        lat: Latitude of the location
        lon: Longitude of the location

    Returns:
        Dict containing typhoon data and weather alerts
    """
    try:
        # Use One Call API to get weather alerts
        url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,hourly,daily&appid={api_key}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        return {
            "alerts": data.get("alerts", []),
            "current": data.get("current", {}),
            "timezone": data.get("timezone", "UTC"),
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching typhoon data: {e}")
        raise CLIWeatherException(
            "Failed to fetch typhoon data. Please check your internet connection and API key."
        )


def view_typhoon_tracker() -> None:
    """View active typhoons and weather alerts for the chosen location."""
    try:
        location_name, lat, lon = get_location_for_weather(
            "to check for typhoons and weather alerts"
        )
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return

    logger.debug(f"Checking typhoons and weather alerts for {location_name}...")
    try:
        data = fetch_typhoon_data(API_KEY, lat, lon)
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return

    print(f"\nWeather Alerts for {location_name}:")

    if not data["alerts"]:
        print("No active weather alerts or typhoons in this area.")
        return

    for alert in data["alerts"]:
        print("\n" + "=" * 50)
        print(f"Alert: {alert['event']}")
        print(f"Severity: {alert['severity'].upper()}")
        print(f"Start: {alert['start']}")
        print(f"End: {alert['end']}")
        print(f"Description: {alert['description']}")
        print("=" * 50)

    if confirm("\nSave alerts to file?"):
        try:
            filename = f"typhoon_alerts_{location_name.replace(' ', '_')}_{time.strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Weather Alerts for {location_name}\n")
                f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for alert in data["alerts"]:
                    f.write("=" * 50 + "\n")
                    f.write(f"Alert: {alert['event']}\n")
                    f.write(f"Severity: {alert['severity'].upper()}\n")
                    f.write(f"Start: {alert['start']}\n")
                    f.write(f"End: {alert['end']}\n")
                    f.write(f"Description: {alert['description']}\n")
                    f.write("=" * 50 + "\n")
            print(f"\nAlerts saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving alerts to file: {e}")
            print("Error saving alerts to file.")
