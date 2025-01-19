import sys
import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__file__)


class CLIWeatherException(Exception):
    """Raise for clear and user friendly error message."""


class CacheManager:
    """Handles caching of data with expiry logic."""

    def __init__(self, cache_dir: Path, expiry: timedelta):
        self.cache_dir = cache_dir
        self.expiry = expiry

    def _generate_key(self, *args) -> str:
        """Generate a unique cache key."""
        key_string = "_".join(map(str, args))
        key = hashlib.md5(key_string.encode()).hexdigest()
        logger.debug("Generated cache key successfully.")
        return key

    def save(self, key: str, data: dict) -> None:
        """Save data to the cache."""
        cache_file = self.cache_dir / key
        with cache_file.open('w') as file:
            json.dump({"timestamp": datetime.now().isoformat(), "data": data}, file)
        logger.debug("Cache file saved successfully.")

    def load(self, key: str) -> dict | None:
        """Load data from the cache if valid."""
        cache_file = self.cache_dir / key
        if not cache_file.exists():
            return None

        with cache_file.open('r') as file:
            cached = json.load(file)
            timestamp = datetime.fromisoformat(cached["timestamp"])
            if datetime.now() - timestamp < self.expiry:
                logger.debug("Loaded cached data successfully.")
                return cached["data"]

        # Expired cache, delete the file
        cache_file.unlink()
        logger.debug("Cache expired, deleted cache file.")
        return None

    def clear(self) -> None:
        """Clear all cached files."""
        for cache_file in self.cache_dir.iterdir():
            cache_file.unlink()
        logger.debug("Cache cleared successfully.")
        print("Cache cleared successfully.")


# === Utility functions ===#
def clear_logs(log_dir):
    """Clears the log file."""
    for file in log_dir.iterdir():
        file.unlink()
    logging.debug("Cleared logs successfully.")
    print("Logs cleared successfully.")


def confirm(prompt: str) -> bool:
    """Prompt user for confirmation."""
    choice = ""
    try:
        while choice not in {"y", "n", "yes", "no"}:
            choice = input(f"{prompt} (Y/n): ").lower()
        return choice in {"y", "yes"}
    except KeyboardInterrupt:
        raise


def get_index(items: List) -> int:
    """Get the index of an item from the given list of items."""
    while True:
        try:
            index = int(input("> "))
            if 1 <= index <= len(items):
                return index - 1
        except ValueError:
            print("Please enter an integer.")
        except KeyboardInterrupt:
            raise


def choose_local_path() -> Path:
    """Choose a local folder to place weather forecast file."""
    def is_hidden(file: Path) -> bool:
        """Checks if a file is hidden."""
        return file.name.startswith(".") and file.name not in (".", "..")

    def contains_subfolder(parent_path: Path) -> bool:
        """Check if a folder contains subfolder(s)."""
        return any(file.is_dir() and not is_hidden(file) for file in parent_path.iterdir())

    def choose_folder(parent_path: Path, prompt: str) -> Path:
        """Choose a folder inside a specified folder."""
        try:
            subfolders = sorted([file for file in parent_path.iterdir() if file.is_dir() and not is_hidden(file)])

            print(prompt)
            for index, folder in enumerate(subfolders, start=1):
                print(f"{index}. {folder.name}")
            return subfolders[get_index(subfolders)]
        except PermissionError as e:
            logging.error(f"Error: no permission to access folder: {e}")
            raise CLIWeatherException("No permission to access folder.")
    
    main_path = Path.home() / "storage/shared" #Make these local variables.
    prompt = "Choose folder to save weather forecast"

    while True:
        chosen_folder = choose_folder(main_path, prompt)
        if confirm(f"Save weather forecast here:'{chosen_folder.name}'?"):
            return chosen_folder
        if contains_subfolder(chosen_folder):
            while contains_subfolder(chosen_folder) and confirm(f"'{chosen_folder.name}' contains subfolders. Go deeper?"):
                print(f"Exploring subfolders in '{chosen_folder.name}'...")
                chosen_folder = choose_folder(chosen_folder, prompt)

                if confirm(f"Save weather forecast here:'{chosen_folder.name}'?"):
                    return chosen_folder


def run_menu(options: List[Dict], prompt: str = "", main: bool = False) -> None:
    """Run menu and execute selected actions."""
    try:
        while True:
            print(f"\n{prompt}")
            print("-" * (len(prompt) + 5))
            for index, option in enumerate(options, start=1):
                print(f"{index}. {list(option)[0]}")
            index = get_index(list(options))
            func = list(options[index].values())[0]
            print()
            if main and func is None:
                logging.debug("App closed.")
                print("Goodbye!")
                sys.exit()
            if func is None:
                break
            func()
    except KeyboardInterrupt:
        raise


def choose(choices: List, add_back: bool = False) -> None:
    """Let user choose an item from a list of choices."""
    for index, item in enumerate(choices, start=1):
        print(f"{index}. {item.title()}")

    return choices[get_index(choices)]
