"""
Rich-based interactive UI for CLI Weather Application.

This module provides a modern interactive menu system using the Rich library
for enhanced visual presentation with tables, progress bars, panels, and styling.
"""

import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.layout import Layout
from rich.align import Align

from ..core.app import WeatherApp
from ..core.location_service import Location
from ..core.weather_service import WeatherData
from ..legacy.utils import CLIWeatherException

logger = logging.getLogger(__name__)


class RichUI:
    """Rich-based interactive UI for the weather application."""
    
    def __init__(self):
        """Initialize the Rich UI."""
        self.console = Console()
        self.app = WeatherApp()
        
    def run(self):
        """Start the main application loop."""
        try:
            self.show_welcome()
            self.main_menu()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Goodbye![/yellow]")
            sys.exit(0)
        except Exception as e:
            self.console.print(f"[red]An unexpected error occurred: {e}[/red]")
            logger.exception(f"Unexpected error: {e}")
            sys.exit(1)
    
    def show_welcome(self):
        """Display welcome screen."""
        welcome_text = """
        # 🌤️  CLI Weather Assistant
        
        Your command-line companion for weather information and forecasts.
        """
        
        welcome_panel = Panel(
            Markdown(welcome_text),
            title="Welcome",
            title_align="center",
            border_style="blue",
            padding=(1, 2),
        )
        
        self.console.print()
        self.console.print(welcome_panel)
        self.console.print()
    
    def main_menu(self):
        """Display and handle main menu."""
        while True:
            try:
                self.console.print("\n[bold blue]═══ MAIN MENU ═══[/bold blue]\n")
                
                choices = [
                    "🌡️  View Weather Forecasts",
                    "📍 Manage Locations", 
                    "🏃 Manage Activities",
                    "🌀 Track Typhoons",
                    "⚙️  Other Options",
                    "❌ Exit"
                ]
                
                choice = self.show_menu(choices, "What would you like to do?")
                
                if choice == 1:
                    self.weather_menu()
                elif choice == 2:
                    self.location_menu()
                elif choice == 3:
                    self.activity_menu()
                elif choice == 4:
                    self.typhoon_tracker()
                elif choice == 5:
                    self.other_menu()
                elif choice == 6:
                    self.console.print("\n[yellow]Goodbye![/yellow]")
                    break
                    
            except CLIWeatherException as e:
                self.console.print(f"[red]Error: {e}[/red]")
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Returning to main menu...[/yellow]")
    
    def show_menu(self, choices: List[str], prompt: str = "Choose an option") -> int:
        """Display menu and get user choice."""
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Choice", style="cyan", width=4)
        table.add_column("Option", style="white")
        
        for i, choice in enumerate(choices, 1):
            table.add_row(str(i), choice)
        
        self.console.print(table)
        
        while True:
            try:
                choice = Prompt.ask(f"\n[bold]{prompt}[/bold]", choices=[str(i) for i in range(1, len(choices) + 1)])
                return int(choice)
            except ValueError:
                self.console.print("[red]Please enter a valid number.[/red]")
    
    def weather_menu(self):
        """Handle weather forecast menu."""
        while True:
            self.console.print("\n[bold green]═══ WEATHER FORECASTS ═══[/bold green]\n")
            
            choices = [
                "☀️  Current Weather",
                "⏰ Hourly Forecast (24hrs)",
                "📅 5-Day Forecast", 
                "🗓️  Specific Day Forecast",
                "🎯 Best Days for Activity",
                "⬅️  Back"
            ]
            
            choice = self.show_menu(choices, "Select forecast type")
            
            if choice == 1:
                self.show_current_weather()
            elif choice == 2:
                self.show_hourly_forecast()
            elif choice == 3:
                self.show_daily_forecast()
            elif choice == 4:
                self.show_specific_day_forecast()
            elif choice == 5:
                self.show_best_activity_days()
            elif choice == 6:
                break
    
    def show_current_weather(self):
        """Display current weather."""
        location = self.choose_location()
        if not location:
            return
            
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
            ) as progress:
                task = progress.add_task("Fetching current weather...", total=None)
                weather = self.app.get_current_weather(location)
                progress.update(task, completed=100)
                
            # Display results outside of progress context
            self.display_current_weather(location, weather)
            
            if Confirm.ask("\n💾 Save current weather to file?"):
                self.save_forecast_to_file(location, [weather])
                
        except CLIWeatherException as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def display_current_weather(self, location: Location, weather: WeatherData):
        """Display current weather in a formatted panel."""
        weather_info = f"""
        📍 **Location:** {location.name}
        🗓️  **Date:** {weather.date}
        🌡️  **Temperature:** {weather.temp:.1f}°C
        🌤️  **Conditions:** {weather.weather.title()}
        💨 **Wind Speed:** {weather.wind_speed:.1f} km/h
        🌧️  **Rain:** {weather.rain} mm
        """
        
        panel = Panel(
            Markdown(weather_info),
            title="Current Weather",
            title_align="center",
            border_style="green",
            padding=(1, 2),
        )
        
        self.console.print()
        self.console.print(panel)
    
    def show_hourly_forecast(self):
        """Display hourly forecast."""
        location = self.choose_location()
        if not location:
            return
            
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
            ) as progress:
                task = progress.add_task("Fetching hourly forecast...", total=None)
                forecast = self.app.get_hourly_forecast(location)
                progress.update(task, completed=100)
                
            self.display_hourly_forecast(location, forecast)
            
            if Confirm.ask("\n💾 Save forecast to file?"):
                self.save_forecast_to_file(location, forecast)
                    
        except CLIWeatherException as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def display_hourly_forecast(self, location: Location, forecast: List[WeatherData]):
        """Display hourly forecast in a table."""
        table = Table(title=f"📋 24-Hour Forecast for {location.name}", box=box.ROUNDED)
        
        table.add_column("🕐 Time", style="cyan", width=12)
        table.add_column("🌡️ Temp", style="yellow", justify="right", width=8)
        table.add_column("🌤️ Weather", style="green", width=20)
        table.add_column("💨 Wind", style="blue", justify="right", width=10)
        table.add_column("🌧️ Rain", style="magenta", justify="right", width=8)
        
        for weather in forecast:
            # Extract time from datetime string
            time_part = weather.date.split(" ")[1][:5]  # Get HH:MM
            table.add_row(
                time_part,
                f"{weather.temp:.1f}°C",
                weather.weather.title(),
                f"{weather.wind_speed:.1f} km/h",
                f"{weather.rain} mm"
            )
        
        self.console.print()
        self.console.print(table)
    
    def show_daily_forecast(self):
        """Display daily forecast."""
        location = self.choose_location()
        if not location:
            return
            
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
            ) as progress:
                task = progress.add_task("Fetching 5-day forecast...", total=None)
                forecast = self.app.get_daily_forecast(location)
                progress.update(task, completed=100)
                
            self.display_daily_forecast(location, forecast)
            
            if Confirm.ask("\n💾 Save forecast to file?"):
                self.save_forecast_to_file(location, forecast)
                    
        except CLIWeatherException as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def display_daily_forecast(self, location: Location, forecast: List[WeatherData]):
        """Display daily forecast in a table."""
        table = Table(title=f"📅 5-Day Forecast for {location.name}", box=box.ROUNDED)
        
        table.add_column("📅 Date", style="cyan", width=12)
        table.add_column("🌡️ Temp", style="yellow", justify="right", width=10)
        table.add_column("🌤️ Weather", style="green", width=25)
        table.add_column("💨 Wind", style="blue", justify="right", width=12)
        table.add_column("🌧️ Rain", style="magenta", justify="right", width=10)
        
        for weather in forecast:
            table.add_row(
                weather.date,
                f"{weather.temp:.1f}°C",
                weather.weather.title(),
                f"{weather.wind_speed:.1f} km/h",
                f"{weather.rain} mm"
            )
        
        self.console.print()
        self.console.print(table)
    
    def show_specific_day_forecast(self):
        """Display forecast for a specific day."""
        location = self.choose_location()
        if not location:
            return
            
        # First get the daily forecast to show available days
        try:
            daily_forecast = self.app.get_daily_forecast(location)
            
            self.console.print(f"\n[bold]Available days for {location.name}:[/bold]")
            
            table = Table(show_header=False, box=box.SIMPLE)
            table.add_column("Day", style="cyan", width=4)
            table.add_column("Date", style="white")
            
            for i, day in enumerate(daily_forecast):
                table.add_row(str(i + 1), day.date)
            
            self.console.print(table)
            
            while True:
                try:
                    choice = Prompt.ask(
                        "\nSelect day number", 
                        choices=[str(i) for i in range(1, len(daily_forecast) + 1)]
                    )
                    day_index = int(choice) - 1
                    break
                except ValueError:
                    self.console.print("[red]Please enter a valid day number.[/red]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
            ) as progress:
                task = progress.add_task("Fetching detailed forecast...", total=None)
                selected_day, hourly_details = self.app.get_specific_day_forecast(location, day_index)
                progress.update(task, completed=100)
            
            self.display_specific_day(location, selected_day, hourly_details)
            
            # Prepare data for saving
            if hourly_details:
                save_data = [selected_day] + hourly_details
            else:
                save_data = [selected_day]
            
            if Confirm.ask("\n💾 Save forecast to file?"):
                self.save_forecast_to_file(location, save_data)
                
        except CLIWeatherException as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def display_specific_day(self, location: Location, day: WeatherData, hourly: List[WeatherData]):
        """Display specific day forecast with hourly details."""
        # Day summary panel
        day_info = f"""
        📅 **Date:** {day.date}
        🌡️ **Temperature:** {day.temp:.1f}°C
        🌤️ **Weather:** {day.weather.title()}
        💨 **Wind Speed:** {day.wind_speed:.1f} km/h
        🌧️ **Rain:** {day.rain} mm
        """
        
        panel = Panel(
            Markdown(day_info),
            title=f"📋 Forecast for {location.name}",
            border_style="green"
        )
        
        self.console.print()
        self.console.print(panel)
        
        # Hourly details if available
        if hourly:
            self.console.print(f"\n[bold]⏰ Hourly details for {day.date}:[/bold]")
            self.display_hourly_forecast(location, hourly)
    
    def show_best_activity_days(self):
        """Display best days for activities."""
        # First choose activity
        activities = self.app.get_activities()
        if not activities:
            self.console.print("[yellow]No activities found. Please add an activity first.[/yellow]")
            return
        
        activity_names = list(activities.keys())
        self.console.print("\n[bold]Select an activity:[/bold]")
        
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Choice", style="cyan", width=4)
        table.add_column("Activity", style="white")
        
        for i, name in enumerate(activity_names, 1):
            table.add_row(str(i), name)
        
        self.console.print(table)
        
        while True:
            try:
                choice = Prompt.ask(
                    "Choose activity", 
                    choices=[str(i) for i in range(1, len(activity_names) + 1)]
                )
                activity_name = activity_names[int(choice) - 1]
                break
            except (ValueError, IndexError):
                self.console.print("[red]Please enter a valid choice.[/red]")
        
        # Then choose location
        location = self.choose_location()
        if not location:
            return
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
            ) as progress:
                task = progress.add_task(f"Finding best days for {activity_name}...", total=None)
                best_days = self.app.get_best_activity_days(location, activity_name)
                progress.update(task, completed=100)
                
            if best_days:
                self.display_activity_forecast(location, activity_name, best_days)
                
                if Confirm.ask("\n💾 Save results to file?"):
                    self.save_forecast_to_file(location, best_days, activity_name)
            else:
                self.console.print(f"[yellow]No suitable days found for {activity_name} in {location.name}[/yellow]")
                    
        except CLIWeatherException as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def display_activity_forecast(self, location: Location, activity: str, forecast: List[WeatherData]):
        """Display best days for activity."""
        table = Table(title=f"🎯 Best Days for {activity.title()} in {location.name}", box=box.ROUNDED)
        
        table.add_column("📅 Date", style="cyan", width=12)
        table.add_column("🌡️ Temp", style="yellow", justify="right", width=10)
        table.add_column("🌤️ Weather", style="green", width=25)
        table.add_column("💨 Wind", style="blue", justify="right", width=12)
        table.add_column("🌧️ Rain", style="magenta", justify="right", width=10)
        
        for weather in forecast:
            table.add_row(
                weather.date,
                f"{weather.temp:.1f}°C",
                weather.weather.title(),
                f"{weather.wind_speed:.1f} km/h",
                f"{weather.rain} mm"
            )
        
        self.console.print()
        self.console.print(table)
    
    def choose_location(self) -> Optional[Location]:
        """Allow user to choose a location."""
        locations = self.app.get_locations(include_sensitive=True)
        
        choices = [
            "🌍 Use current location (auto-detect)",
            "🔍 Search for a location",
            "📝 Enter coordinates manually"
        ]
        
        # Add saved locations
        if locations:
            choices.insert(0, "📍 Choose from saved locations")
        
        self.console.print("\n[bold]Choose location option:[/bold]")
        choice = self.show_menu(choices)
        
        try:
            if choice == 1 and locations:
                # Choose from saved locations
                location_names = list(locations.keys())
                
                self.console.print("\n[bold]Saved locations:[/bold]")
                table = Table(show_header=False, box=box.SIMPLE)
                table.add_column("Choice", style="cyan", width=4)
                table.add_column("Location", style="white")
                
                for i, name in enumerate(location_names, 1):
                    table.add_row(str(i), name)
                
                self.console.print(table)
                
                loc_choice = Prompt.ask(
                    "Select location", 
                    choices=[str(i) for i in range(1, len(location_names) + 1)]
                )
                location_name = location_names[int(loc_choice) - 1]
                return locations[location_name]
                
            elif (choice == 1 and not locations) or (choice == 2 and locations):
                # Use current location
                return self.app.get_current_location()
                
            elif (choice == 2 and not locations) or (choice == 3 and locations):
                # Search for location
                query = Prompt.ask("Enter location name")
                return self.app.geocode_address(query)
                
            elif (choice == 3 and not locations) or (choice == 4 and locations):
                # Manual coordinates
                lat_str = Prompt.ask("Enter latitude")
                lon_str = Prompt.ask("Enter longitude") 
                name = Prompt.ask("Enter name for this location")
                
                try:
                    lat = float(lat_str)
                    lon = float(lon_str)
                    return self.app.create_location_from_coordinates(name, lat, lon)
                except ValueError:
                    self.console.print("[red]Invalid coordinates. Please enter numeric values.[/red]")
                    return None
                    
        except CLIWeatherException as e:
            self.console.print(f"[red]Error: {e}[/red]")
            return None
        except KeyboardInterrupt:
            return None
        
        return None
    
    def location_menu(self):
        """Handle location management menu."""
        while True:
            self.console.print("\n[bold blue]═══ LOCATION MANAGEMENT ═══[/bold blue]\n")
            
            choices = [
                "👀 View Locations",
                "➕ Add Location",
                "💾 Save Current Location", 
                "🔍 Search Location",
                "🗑️  Delete Location",
                "⬅️  Back"
            ]
            
            choice = self.show_menu(choices)
            
            if choice == 1:
                self.view_locations()
            elif choice == 2:
                self.add_location()
            elif choice == 3:
                self.save_current_location()
            elif choice == 4:
                self.search_location()
            elif choice == 5:
                self.delete_location()
            elif choice == 6:
                break
    
    def view_locations(self):
        """Display all saved locations."""
        locations = self.app.get_locations(include_sensitive=True)
        
        if not locations:
            self.console.print("[yellow]No locations found. Please add a location first.[/yellow]")
            return
        
        table = Table(title="📍 Your Saved Locations", box=box.ROUNDED)
        table.add_column("Name", style="cyan", width=20)
        table.add_column("Coordinates", style="white", width=20)
        
        for name, location in locations.items():
            table.add_row(name, f"{location.latitude:.4f}, {location.longitude:.4f}")
        
        self.console.print()
        self.console.print(table)
    
    def add_location(self):
        """Add a new location."""
        name = Prompt.ask("Enter location name")
        
        method = self.show_menu([
            "🔍 Search by address",
            "📍 Enter coordinates manually"
        ], "How would you like to add this location?")
        
        try:
            if method == 1:
                address = Prompt.ask("Enter address to search")
                location = self.app.geocode_address(address)
                location.name = name  # Use user-provided name
            else:
                lat_str = Prompt.ask("Enter latitude")
                lon_str = Prompt.ask("Enter longitude")
                
                lat = float(lat_str)
                lon = float(lon_str)
                location = self.app.create_location_from_coordinates(name, lat, lon)
            
            self.app.save_location(location)
            self.console.print(f"[green]✅ Location '{name}' saved successfully![/green]")
            
        except ValueError:
            self.console.print("[red]Invalid coordinates. Please enter numeric values.[/red]")
        except CLIWeatherException as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def save_current_location(self):
        """Save current location based on IP."""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
            ) as progress:
                task = progress.add_task("Detecting current location...", total=None)
                location = self.app.get_current_location()
                progress.update(task, completed=100)
            
            name = Prompt.ask("Enter name for this location", default="My Current Location")
            location.name = name
            
            self.app.save_location(location)
            self.console.print(f"[green]✅ Current location saved as '{name}'![/green]")
            
        except CLIWeatherException as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def search_location(self):
        """Search for a location."""
        query = Prompt.ask("Enter location to search")
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
            ) as progress:
                task = progress.add_task("Searching location...", total=None)
                location = self.app.geocode_address(query)
                progress.update(task, completed=100)
            
            # Display location info
            location_info = f"""
            📍 **Name:** {location.name}
            🌍 **Coordinates:** {location.latitude:.4f}, {location.longitude:.4f}
            """
            
            panel = Panel(
                Markdown(location_info),
                title="Location Found",
                border_style="green"
            )
            
            self.console.print()
            self.console.print(panel)
            
            if Confirm.ask("Save this location?"):
                save_name = Prompt.ask("Enter name for this location", default=location.name)
                location.name = save_name
                self.app.save_location(location)
                self.console.print(f"[green]✅ Location saved as '{save_name}'![/green]")
            
        except CLIWeatherException as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def delete_location(self):
        """Delete a saved location."""
        locations = self.app.get_locations()
        
        if not locations:
            self.console.print("[yellow]No locations to delete.[/yellow]")
            return
        
        location_names = list(locations.keys())
        
        self.console.print("\n[bold]Select location to delete:[/bold]")
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Choice", style="red", width=4)
        table.add_column("Location", style="white")
        
        for i, name in enumerate(location_names, 1):
            table.add_row(str(i), name)
        
        self.console.print(table)
        
        try:
            choice = Prompt.ask(
                "Select location to delete", 
                choices=[str(i) for i in range(1, len(location_names) + 1)]
            )
            location_name = location_names[int(choice) - 1]
            
            if Confirm.ask(f"Are you sure you want to delete '{location_name}'?"):
                if self.app.delete_location(location_name):
                    self.console.print(f"[green]✅ Location '{location_name}' deleted successfully![/green]")
                else:
                    self.console.print(f"[yellow]Location '{location_name}' not found.[/yellow]")
        
        except (ValueError, IndexError):
            self.console.print("[red]Invalid selection.[/red]")
    
    def activity_menu(self):
        """Handle activity management menu."""
        while True:
            self.console.print("\n[bold green]═══ ACTIVITY MANAGEMENT ═══[/bold green]\n")
            
            choices = [
                "👀 View Activities",
                "➕ Add Activity",
                "✏️  Edit Activity",
                "🗑️  Delete Activity",
                "⬅️  Back"
            ]
            
            choice = self.show_menu(choices)
            
            if choice == 1:
                self.view_activities()
            elif choice == 2:
                self.add_activity()
            elif choice == 3:
                self.edit_activity()
            elif choice == 4:
                self.delete_activity()
            elif choice == 5:
                break
    
    def view_activities(self):
        """Display all saved activities."""
        activities = self.app.get_activities()
        
        if not activities:
            self.console.print("[yellow]No activities found. Please add an activity first.[/yellow]")
            return
        
        table = Table(title="🏃 Your Activities", box=box.ROUNDED)
        table.add_column("Activity", style="cyan", width=15)
        table.add_column("Temperature", style="yellow", width=12)
        table.add_column("Rain (max)", style="blue", width=10)
        table.add_column("Wind Range", style="green", width=15)
        table.add_column("Time Range", style="magenta", width=15)
        
        for name, activity in activities.items():
            temp_range = f"{activity.temp_min}-{activity.temp_max}°C"
            wind_range = f"{activity.wind_min}-{activity.wind_max} km/h"
            time_range = f"{activity.time_range[0]}-{activity.time_range[1]}"
            
            table.add_row(
                name,
                temp_range,
                f"{activity.rain} mm",
                wind_range,
                time_range
            )
        
        self.console.print()
        self.console.print(table)
    
    def add_activity(self):
        """Add a new activity."""
        self.console.print("\n[bold]Creating new activity...[/bold]\n")
        
        name = Prompt.ask("Activity name")
        
        # Temperature range
        try:
            temp_min = int(Prompt.ask("Minimum temperature (°C)", default="0"))
            temp_max = int(Prompt.ask("Maximum temperature (°C)", default="30"))
            
            if temp_min >= temp_max:
                self.console.print("[red]Minimum temperature must be less than maximum temperature.[/red]")
                return
        except ValueError:
            self.console.print("[red]Please enter valid temperatures.[/red]")
            return
        
        # Rain
        try:
            rain = float(Prompt.ask("Maximum rain (mm)", default="0"))
        except ValueError:
            self.console.print("[red]Please enter a valid rain value.[/red]")
            return
        
        # Wind range
        try:
            wind_min = float(Prompt.ask("Minimum wind speed (km/h)", default="0"))
            wind_max = float(Prompt.ask("Maximum wind speed (km/h)", default="20"))
            
            if wind_min > wind_max:
                self.console.print("[red]Minimum wind speed must be less than or equal to maximum wind speed.[/red]")
                return
        except ValueError:
            self.console.print("[red]Please enter valid wind speeds.[/red]")
            return
        
        # Time range (optional)
        if Confirm.ask("Specify time range for this activity?", default=False):
            start_time = Prompt.ask("Start time (HH:MM)", default="00:00")
            end_time = Prompt.ask("End time (HH:MM)", default="23:59")
            time_range = [start_time, end_time]
        else:
            time_range = None
        
        try:
            activity = self.app.create_activity(
                name, temp_min, temp_max, rain, wind_max, wind_min, time_range
            )
            self.app.save_activity(activity)
            self.console.print(f"[green]✅ Activity '{name}' created successfully![/green]")
            
        except CLIWeatherException as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def edit_activity(self):
        """Edit an existing activity."""
        activities = self.app.get_activities()
        
        if not activities:
            self.console.print("[yellow]No activities to edit.[/yellow]")
            return
        
        activity_names = list(activities.keys())
        
        self.console.print("\n[bold]Select activity to edit:[/bold]")
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Choice", style="cyan", width=4)
        table.add_column("Activity", style="white")
        
        for i, name in enumerate(activity_names, 1):
            table.add_row(str(i), name)
        
        self.console.print(table)
        
        try:
            choice = Prompt.ask(
                "Select activity", 
                choices=[str(i) for i in range(1, len(activity_names) + 1)]
            )
            activity_name = activity_names[int(choice) - 1]
            activity = activities[activity_name]
            
            self.console.print(f"\n[bold]Editing '{activity_name}':[/bold]")
            self.console.print("[dim](Press Enter to keep current value)[/dim]\n")
            
            # Edit each field
            temp_min_str = Prompt.ask("Minimum temperature (°C)", default=str(activity.temp_min))
            temp_max_str = Prompt.ask("Maximum temperature (°C)", default=str(activity.temp_max))
            rain_str = Prompt.ask("Maximum rain (mm)", default=str(activity.rain))
            wind_min_str = Prompt.ask("Minimum wind speed (km/h)", default=str(activity.wind_min))
            wind_max_str = Prompt.ask("Maximum wind speed (km/h)", default=str(activity.wind_max))
            
            start_time = Prompt.ask("Start time (HH:MM)", default=activity.time_range[0])
            end_time = Prompt.ask("End time (HH:MM)", default=activity.time_range[1])
            
            # Create updated activity
            updated_activity = self.app.create_activity(
                activity_name,
                int(temp_min_str),
                int(temp_max_str),
                float(rain_str),
                float(wind_max_str),
                float(wind_min_str),
                [start_time, end_time]
            )
            
            self.app.save_activity(updated_activity)
            self.console.print(f"[green]✅ Activity '{activity_name}' updated successfully![/green]")
            
        except (ValueError, IndexError):
            self.console.print("[red]Invalid selection or values.[/red]")
        except CLIWeatherException as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def delete_activity(self):
        """Delete an existing activity."""
        activities = self.app.get_activities()
        
        if not activities:
            self.console.print("[yellow]No activities to delete.[/yellow]")
            return
        
        activity_names = list(activities.keys())
        
        self.console.print("\n[bold]Select activity to delete:[/bold]")
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Choice", style="red", width=4)
        table.add_column("Activity", style="white")
        
        for i, name in enumerate(activity_names, 1):
            table.add_row(str(i), name)
        
        self.console.print(table)
        
        try:
            choice = Prompt.ask(
                "Select activity to delete", 
                choices=[str(i) for i in range(1, len(activity_names) + 1)]
            )
            activity_name = activity_names[int(choice) - 1]
            
            if Confirm.ask(f"Are you sure you want to delete '{activity_name}'?"):
                if self.app.delete_activity(activity_name):
                    self.console.print(f"[green]✅ Activity '{activity_name}' deleted successfully![/green]")
                else:
                    self.console.print(f"[yellow]Activity '{activity_name}' not found.[/yellow]")
        
        except (ValueError, IndexError):
            self.console.print("[red]Invalid selection.[/red]")
    
    def typhoon_tracker(self):
        """Track typhoons and weather alerts."""
        location = self.choose_location()
        if not location:
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ) as progress:
            task = progress.add_task("Fetching weather alerts...", total=None)
            
            try:
                alerts_data = self.app.get_typhoon_alerts(location)
                progress.update(task, completed=100)
                
                self.display_typhoon_alerts(location, alerts_data)
                
                if alerts_data.get("alerts") and Confirm.ask("\n💾 Save alerts to file?"):
                    file_path = self.choose_save_path()
                    if file_path:
                        self.app.save_typhoon_alerts_to_file(location, alerts_data, file_path)
                        self.console.print("[green]✅ Alerts saved successfully![/green]")
                
            except CLIWeatherException as e:
                progress.stop()
                self.console.print(f"[red]Error: {e}[/red]")
    
    def display_typhoon_alerts(self, location: Location, alerts_data: Dict):
        """Display typhoon alerts and weather information."""
        self.console.print(f"\n[bold]🌀 Weather Alerts for {location.name}[/bold]\n")
        
        alerts = alerts_data.get("alerts", [])
        
        if not alerts:
            self.console.print("[yellow]🌤️  No active weather alerts or typhoons in this area.[/yellow]")
            return
        
        for alert in alerts:
            alert_info = f"""
            🚨 **Alert:** {alert['event']}
            ⚠️  **Severity:** {alert['severity'].upper()}
            🕐 **Start:** {alert['start']}
            🕐 **End:** {alert['end']}
            📝 **Description:** {alert['description']}
            """
            
            severity_colors = {
                'minor': 'yellow',
                'moderate': 'orange',
                'severe': 'red',
                'extreme': 'bright_red'
            }
            
            color = severity_colors.get(alert['severity'].lower(), 'white')
            
            panel = Panel(
                Markdown(alert_info),
                title="Weather Alert",
                border_style=color,
                padding=(1, 2)
            )
            
            self.console.print(panel)
    
    def other_menu(self):
        """Handle other options menu."""
        while True:
            self.console.print("\n[bold magenta]═══ OTHER OPTIONS ═══[/bold magenta]\n")
            
            choices = [
                "🗑️  Clear Cached Data",
                "📄 Clear Logs",
                "⬅️  Back"
            ]
            
            choice = self.show_menu(choices)
            
            if choice == 1:
                if Confirm.ask("Clear all cached weather data?"):
                    self.app.clear_cache()
                    self.console.print("[green]✅ Cache cleared successfully![/green]")
            elif choice == 2:
                if Confirm.ask("Clear all application logs?"):
                    self.app.clear_logs()
                    self.console.print("[green]✅ Logs cleared successfully![/green]")
            elif choice == 3:
                break
    
    def save_forecast_to_file(self, location: Location, forecast: List[WeatherData], activity: Optional[str] = None):
        """Save forecast data to a file."""
        file_path = self.choose_save_path()
        if file_path:
            try:
                self.app.save_weather_to_file(location, forecast, file_path, activity)
                self.console.print("[green]✅ Forecast saved successfully![/green]")
            except CLIWeatherException as e:
                self.console.print(f"[red]Error saving file: {e}[/red]")
    
    def choose_save_path(self) -> Optional[Path]:
        """Choose path to save files."""
        default_path = Path.home() / "Downloads"
        
        if Confirm.ask(f"Save to default location ({default_path})?", default=True):
            return default_path
        else:
            custom_path = Prompt.ask("Enter path to save file", default=str(default_path))
            path = Path(custom_path)
            
            if not path.exists():
                if Confirm.ask(f"Directory '{path}' doesn't exist. Create it?"):
                    try:
                        path.mkdir(parents=True, exist_ok=True)
                        return path
                    except Exception as e:
                        self.console.print(f"[red]Error creating directory: {e}[/red]")
                        return None
                else:
                    return None
            
            return path
