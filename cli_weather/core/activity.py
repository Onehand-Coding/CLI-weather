import logging
from typing import Dict, Tuple
import requests
import geopy
from geopy.geocoders import Nominatim
from ..config import VARS, UNITS, load_config, save_config
from ..utils import CLIWeatherException, confirm, get_index, choose

logger = logging.getLogger(__file__)


# === Activity management functions === #
def save_activity(activity_name: str, criteria: Dict) -> None:
    """Write configured set of criteria for each activity in configuration file."""
    logger.debug(f"Saving activity: {activity_name}")
    configuration = load_config()
    configuration.setdefault("activities", {})[activity_name] = criteria
    save_config(configuration)
    logger.debug(f"'{activity_name}' saved successfully.")


def get_activity_criteria(activity: str) -> Dict:
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
            raise


def choose_activity(task: str = None) -> str:
    """Let user choose an activity."""
    config = load_config()
    activities = config.get("activities", {})
    if not activities:
        logger.error("Cannot choose activity, No activities configured.")
        print("No activities found. Please add an activity first.")
        return

    prompt = f"Choose an activity to {task}." if task else "Choose an activity."
    print(prompt)
    # Add option to go back to previous menu.
    activity_names = list(activities)
    activity_names.append("Back")
    activity_name = choose(activity_names)
    return activity_name


def view_activities() -> None:
    """View existing activity-criteria configurations."""
    activities = load_config().get("activities", {})
    if not activities:
        print("No activities found. Please add an activity first.")
        return None
    print("\nYour Activities:\n")
    for activity, criteria in activities.items():
        print(f"\t{activity.title()}:")
        for key, value in criteria.items():
            unit = UNITS.get(key, "")
            if isinstance(value, list) and len(value) == 2:
                print(f"\t\t{key.replace('_', ' ').title()}: {value[0]} to {value[1]} {unit}")
            else:
                print(f"\t\t{key.replace('_', ' ').title()}: {value} {unit}")


def add_activity() -> None:
    """Add new activity-criteria configuration."""
    activity_name = ""
    while not activity_name:
        activity_name = input("Enter activity name: ").lower().strip()
    criteria = get_activity_criteria(activity_name)
    if confirm("Save activity?"):
        save_activity(activity_name, criteria)
        print(f"\n{activity_name.title()} activity added successfully.")


def edit_activity() -> None:
    """Edit existing criteria for an activity."""
    activity_name = choose_activity("edit")
    if not activity_name:
        return
    if activity_name == "Back":
        return
    current_criteria = load_config().get("activities", {})[activity_name]
    print(f"Current criteria for {activity_name.title()}:")
    for key, value in current_criteria.items():
        unit = UNITS.get(key, "")
        if isinstance(value, list) and len(value) == 2:  # Handle range values like time_range
            print(f"  {key.replace('_', ' ').title()}: {value[0]} to {value[1]} {unit}")
        else:
            print(f"  {key.replace('_', ' ').title()}: {value} {unit}")

    new_criteria = get_activity_criteria(activity_name)
    if confirm("Save changes?"):
        save_activity(activity_name, new_criteria)
        print(f"Criteria for {activity_name.title()} updated successfully.")


def delete_activity() -> None:
    """Let user remove an existing activity-criteria configuration."""
    activity_name = choose_activity("remove")
    if not activity_name:
        return
    if activity_name == "Back":
        return
    config = load_config()
    activities= config.get("activities")
    if not activities:
        logger.error("No activities configured.")
        print("No activities found, Please add one first.")
        return
    if confirm(f"Do you want to remove this activity? {activity_name}:  {activities[activity_name]}"):
        del config["activities"][activity_name]
        save_config(config)
        print(f"\n{activity_name.title()} activity removed successfully.")
