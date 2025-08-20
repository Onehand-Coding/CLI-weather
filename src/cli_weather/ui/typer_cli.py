"""
Typer-based command-line interface for CLI Weather Application.

This module provides a command-line interface using Typer for scriptable usage.
It exposes weather functions as CLI commands with options and arguments, 
enabling automation and scripting capabilities.
"""

import sys
import logging
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box

from ..core.app import WeatherApp
from ..core.models import Location  
from ..core.weather_service import WeatherData
from ..legacy.utils import CLIWeatherException

logger = logging.getLogger(__name__)

# Create the main typer app
app = typer.Typer(
    help="CLI Weather Assistant - Command Line Interface",
    no_args_is_help=True,
    rich_markup_mode="rich"
)

# Create subcommand groups
weather_app = typer.Typer(help="Weather forecast commands")
location_app = typer.Typer(help="Location management commands")
activity_app = typer.Typer(help="Activity management commands")
config_app = typer.Typer(help="Configuration and utility commands")

app.add_typer(weather_app, name="weather")
app.add_typer(location_app, name="location") 
app.add_typer(activity_app, name="activity")
app.add_typer(config_app, name="config")

# Initialize console and weather app
console = Console()
weather_service = WeatherApp()


# Helper functions
def get_location_by_name(location_name: str) -> Location:
    """Get a location by name from saved locations."""
    locations = weather_service.get_locations(include_sensitive=True)
    if location_name in locations:
        return locations[location_name]
    else:
        raise typer.BadParameter(f"Location '{location_name}' not found. Use 'location list' to see available locations.")


def get_location_from_args(
    location: Optional[str] = None,
    latitude: Optional[float] = None, 
    longitude: Optional[float] = None,
    current: bool = False
) -> Location:
    """Get location from command line arguments."""
    if current:
        return weather_service.get_current_location()
    elif location:
        return get_location_by_name(location)
    elif latitude is not None and longitude is not None:
        return weather_service.create_location_from_coordinates("Custom Location", latitude, longitude)
    else:
        raise typer.BadParameter("Must specify --location, --lat/--lon, or --current")


def format_weather_table(forecast: List[WeatherData], title: str) -> Table:
    """Format weather data as a Rich table."""
    table = Table(title=title, box=box.ROUNDED)
    table.add_column("Date", style="cyan")
    table.add_column("Temp", style="yellow", justify="right")
    table.add_column("Weather", style="green")
    table.add_column("Wind", style="blue", justify="right")
    table.add_column("Rain", style="magenta", justify="right")
    
    for weather in forecast:
        table.add_row(
            weather.date,
            f"{weather.temp:.1f}°C",
            weather.weather.title(),
            f"{weather.wind_speed:.1f} km/h",
            f"{weather.rain} mm"
        )
    
    return table


def save_forecast_data(
    location: Location, 
    forecast: List[WeatherData],
    output_file: Optional[Path],
    activity: Optional[str] = None
):
    """Save forecast data to file if output specified."""
    if output_file:
        try:
            weather_service.save_weather_to_file(location, forecast, output_file.parent, activity)
            console.print(f"[green]✅ Forecast saved to {output_file}[/green]")
        except CLIWeatherException as e:
            console.print(f"[red]Error saving file: {e}[/red]")
            raise typer.Exit(1)


# Weather commands
@weather_app.command("current")
def current_weather(
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Saved location name"),
    latitude: Optional[float] = typer.Option(None, "--lat", help="Latitude coordinate"),
    longitude: Optional[float] = typer.Option(None, "--lon", help="Longitude coordinate"),
    current: bool = typer.Option(False, "--current", "-c", help="Use current location (auto-detect)"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format")
):
    """Get current weather for a location."""
    try:
        loc = get_location_from_args(location, latitude, longitude, current)
        weather = weather_service.get_current_weather(loc)
        
        if json_output:
            import json
            data = weather.to_dict()
            data["location"] = loc.name
            console.print(json.dumps(data, indent=2))
        else:
            weather_info = f"""
            📍 **Location:** {loc.name}
            🗓️  **Date:** {weather.date}
            🌡️  **Temperature:** {weather.temp:.1f}°C
            🌤️  **Conditions:** {weather.weather.title()}
            💨 **Wind Speed:** {weather.wind_speed:.1f} km/h
            🌧️  **Rain:** {weather.rain} mm
            """
            
            panel = Panel(
                Markdown(weather_info),
                title="Current Weather",
                border_style="green"
            )
            console.print(panel)
            
    except (CLIWeatherException, typer.BadParameter) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@weather_app.command("hourly")
def hourly_forecast(
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Saved location name"),
    latitude: Optional[float] = typer.Option(None, "--lat", help="Latitude coordinate"),
    longitude: Optional[float] = typer.Option(None, "--lon", help="Longitude coordinate"),
    current: bool = typer.Option(False, "--current", "-c", help="Use current location (auto-detect)"),
    hours: int = typer.Option(24, "--hours", "-h", help="Number of hours to forecast", min=1, max=120),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save to file"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format")
):
    """Get hourly weather forecast for a location."""
    try:
        loc = get_location_from_args(location, latitude, longitude, current)
        forecast = weather_service.get_hourly_forecast(loc, hours)
        
        if json_output:
            import json
            data = {
                "location": loc.name,
                "forecast": [weather.to_dict() for weather in forecast]
            }
            console.print(json.dumps(data, indent=2))
        else:
            table = format_weather_table(forecast, f"📋 {hours}-Hour Forecast for {loc.name}")
            console.print(table)
        
        save_forecast_data(loc, forecast, output)
            
    except (CLIWeatherException, typer.BadParameter) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@weather_app.command("daily") 
def daily_forecast(
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Saved location name"),
    latitude: Optional[float] = typer.Option(None, "--lat", help="Latitude coordinate"),
    longitude: Optional[float] = typer.Option(None, "--lon", help="Longitude coordinate"),
    current: bool = typer.Option(False, "--current", "-c", help="Use current location (auto-detect)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save to file"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format")
):
    """Get 5-day weather forecast for a location."""
    try:
        loc = get_location_from_args(location, latitude, longitude, current)
        forecast = weather_service.get_daily_forecast(loc)
        
        if json_output:
            import json
            data = {
                "location": loc.name,
                "forecast": [weather.to_dict() for weather in forecast]
            }
            console.print(json.dumps(data, indent=2))
        else:
            table = format_weather_table(forecast, f"📅 5-Day Forecast for {loc.name}")
            console.print(table)
        
        save_forecast_data(loc, forecast, output)
            
    except (CLIWeatherException, typer.BadParameter) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@weather_app.command("day")
def specific_day(
    day: int = typer.Argument(help="Day number (1-5) within 5-day forecast"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Saved location name"),
    latitude: Optional[float] = typer.Option(None, "--lat", help="Latitude coordinate"),
    longitude: Optional[float] = typer.Option(None, "--lon", help="Longitude coordinate"),
    current: bool = typer.Option(False, "--current", "-c", help="Use current location (auto-detect)"),
    hourly: bool = typer.Option(False, "--hourly", help="Show hourly details for the day"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format")
):
    """Get forecast for a specific day (1-5)."""
    if day < 1 or day > 5:
        console.print("[red]Day must be between 1 and 5[/red]")
        raise typer.Exit(1)
    
    try:
        loc = get_location_from_args(location, latitude, longitude, current)
        selected_day, hourly_details = weather_service.get_specific_day_forecast(loc, day - 1)
        
        if json_output:
            import json
            data = {
                "location": loc.name,
                "day": selected_day.to_dict(),
                "hourly": [h.to_dict() for h in hourly_details] if hourly else []
            }
            console.print(json.dumps(data, indent=2))
        else:
            # Day summary
            day_info = f"""
            📅 **Date:** {selected_day.date}
            🌡️ **Temperature:** {selected_day.temp:.1f}°C
            🌤️ **Weather:** {selected_day.weather.title()}
            💨 **Wind Speed:** {selected_day.wind_speed:.1f} km/h
            🌧️ **Rain:** {selected_day.rain} mm
            """
            
            panel = Panel(
                Markdown(day_info),
                title=f"📋 Day {day} Forecast for {loc.name}",
                border_style="green"
            )
            console.print(panel)
            
            # Hourly details if requested
            if hourly and hourly_details:
                table = format_weather_table(hourly_details, f"⏰ Hourly Details for {selected_day.date}")
                console.print(table)
            
    except (CLIWeatherException, typer.BadParameter) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@weather_app.command("activity")
def best_activity_days(
    activity: str = typer.Argument(help="Activity name"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Saved location name"),
    latitude: Optional[float] = typer.Option(None, "--lat", help="Latitude coordinate"),
    longitude: Optional[float] = typer.Option(None, "--lon", help="Longitude coordinate"),
    current: bool = typer.Option(False, "--current", "-c", help="Use current location (auto-detect)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save to file"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format")
):
    """Find best days for a specific activity."""
    try:
        loc = get_location_from_args(location, latitude, longitude, current)
        best_days = weather_service.get_best_activity_days(loc, activity)
        
        if not best_days:
            console.print(f"[yellow]No suitable days found for {activity} in {loc.name}[/yellow]")
            return
        
        if json_output:
            import json
            data = {
                "location": loc.name,
                "activity": activity,
                "best_days": [weather.to_dict() for weather in best_days]
            }
            console.print(json.dumps(data, indent=2))
        else:
            table = format_weather_table(best_days, f"🎯 Best Days for {activity.title()} in {loc.name}")
            console.print(table)
        
        save_forecast_data(loc, best_days, output, activity)
            
    except (CLIWeatherException, typer.BadParameter) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@weather_app.command("alerts")
def typhoon_alerts(
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Saved location name"),
    latitude: Optional[float] = typer.Option(None, "--lat", help="Latitude coordinate"),
    longitude: Optional[float] = typer.Option(None, "--lon", help="Longitude coordinate"),
    current: bool = typer.Option(False, "--current", "-c", help="Use current location (auto-detect)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save to file"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format")
):
    """Get weather alerts and typhoon information."""
    try:
        loc = get_location_from_args(location, latitude, longitude, current)
        alerts_data = weather_service.get_typhoon_alerts(loc)
        
        if json_output:
            import json
            console.print(json.dumps(alerts_data, indent=2))
        else:
            alerts = alerts_data.get("alerts", [])
            
            if not alerts:
                console.print(f"[yellow]🌤️  No active weather alerts for {loc.name}[/yellow]")
                return
            
            console.print(f"\n[bold]🌀 Weather Alerts for {loc.name}[/bold]\n")
            
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
                    border_style=color
                )
                console.print(panel)
        
        if output and alerts_data.get("alerts"):
            weather_service.save_typhoon_alerts_to_file(loc, alerts_data, output.parent)
            console.print(f"[green]✅ Alerts saved to {output}[/green]")
            
    except (CLIWeatherException, typer.BadParameter) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# Location commands
@location_app.command("list")
def list_locations(
    include_sensitive: bool = typer.Option(False, "--all", help="Include sensitive locations from environment")
):
    """List all saved locations."""
    locations = weather_service.get_locations(include_sensitive=include_sensitive)
    
    if not locations:
        console.print("[yellow]No locations found.[/yellow]")
        return
    
    table = Table(title="📍 Saved Locations", box=box.ROUNDED)
    table.add_column("Name", style="cyan")
    table.add_column("Coordinates", style="white")
    
    for name, location in locations.items():
        table.add_row(name, f"{location.latitude:.4f}, {location.longitude:.4f}")
    
    console.print(table)


@location_app.command("add")
def add_location(
    name: str = typer.Argument(help="Location name"),
    latitude: Optional[float] = typer.Option(None, "--lat", help="Latitude coordinate"),
    longitude: Optional[float] = typer.Option(None, "--lon", help="Longitude coordinate"),
    address: Optional[str] = typer.Option(None, "--address", help="Address to geocode")
):
    """Add a new location."""
    try:
        if latitude is not None and longitude is not None:
            location = weather_service.create_location_from_coordinates(name, latitude, longitude)
        elif address:
            location = weather_service.geocode_address(address)
            location.name = name
        else:
            console.print("[red]Must provide either --lat/--lon or --address[/red]")
            raise typer.Exit(1)
        
        weather_service.save_location(location)
        console.print(f"[green]✅ Location '{name}' added successfully[/green]")
        
    except CLIWeatherException as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@location_app.command("current")
def save_current_location(
    name: str = typer.Option("My Current Location", "--name", "-n", help="Name for current location")
):
    """Save current location (auto-detected)."""
    try:
        location = weather_service.get_current_location()
        location.name = name
        weather_service.save_location(location)
        
        console.print(f"[green]✅ Current location saved as '{name}'[/green]")
        console.print(f"Coordinates: {location.latitude:.4f}, {location.longitude:.4f}")
        
    except CLIWeatherException as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@location_app.command("search")
def search_location(
    query: str = typer.Argument(help="Location query to search"),
    save: bool = typer.Option(False, "--save", help="Save the found location"),
    name: Optional[str] = typer.Option(None, "--name", help="Name to save location as")
):
    """Search for a location."""
    try:
        location = weather_service.geocode_address(query)
        
        console.print(f"[green]📍 Found: {location.name}[/green]")
        console.print(f"Coordinates: {location.latitude:.4f}, {location.longitude:.4f}")
        
        if save:
            save_name = name or location.name
            location.name = save_name
            weather_service.save_location(location)
            console.print(f"[green]✅ Location saved as '{save_name}'[/green]")
            
    except CLIWeatherException as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@location_app.command("remove")
def remove_location(
    name: str = typer.Argument(help="Location name to remove")
):
    """Remove a saved location."""
    try:
        if weather_service.delete_location(name):
            console.print(f"[green]✅ Location '{name}' removed successfully[/green]")
        else:
            console.print(f"[yellow]Location '{name}' not found[/yellow]")
            
    except CLIWeatherException as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# Activity commands
@activity_app.command("list")
def list_activities():
    """List all saved activities."""
    activities = weather_service.get_activities()
    
    if not activities:
        console.print("[yellow]No activities found.[/yellow]")
        return
    
    table = Table(title="🏃 Your Activities", box=box.ROUNDED)
    table.add_column("Activity", style="cyan")
    table.add_column("Temperature", style="yellow")
    table.add_column("Rain (max)", style="blue")
    table.add_column("Wind Range", style="green")
    table.add_column("Time Range", style="magenta")
    
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
    
    console.print(table)


@activity_app.command("add")
def add_activity(
    name: str = typer.Argument(help="Activity name"),
    temp_min: int = typer.Option(0, "--temp-min", help="Minimum temperature (°C)"),
    temp_max: int = typer.Option(30, "--temp-max", help="Maximum temperature (°C)"),
    rain: float = typer.Option(0.0, "--rain", help="Maximum rain (mm)"),
    wind_min: float = typer.Option(0.0, "--wind-min", help="Minimum wind speed (km/h)"),
    wind_max: float = typer.Option(20.0, "--wind-max", help="Maximum wind speed (km/h)"),
    start_time: str = typer.Option("00:00", "--start", help="Start time (HH:MM)"),
    end_time: str = typer.Option("23:59", "--end", help="End time (HH:MM)")
):
    """Add a new activity with weather criteria."""
    try:
        activity = weather_service.create_activity(
            name, temp_min, temp_max, rain, wind_max, wind_min, [start_time, end_time]
        )
        weather_service.save_activity(activity)
        console.print(f"[green]✅ Activity '{name}' added successfully[/green]")
        
    except CLIWeatherException as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@activity_app.command("remove")
def remove_activity(
    name: str = typer.Argument(help="Activity name to remove")
):
    """Remove a saved activity."""
    try:
        if weather_service.delete_activity(name):
            console.print(f"[green]✅ Activity '{name}' removed successfully[/green]")
        else:
            console.print(f"[yellow]Activity '{name}' not found[/yellow]")
            
    except CLIWeatherException as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@activity_app.command("show")
def show_activity(
    name: str = typer.Argument(help="Activity name")
):
    """Show details of a specific activity."""
    try:
        activity = weather_service.get_activity(name)
        
        if not activity:
            console.print(f"[yellow]Activity '{name}' not found[/yellow]")
            return
        
        activity_info = f"""
        🎯 **Activity:** {activity.name}
        🌡️ **Temperature Range:** {activity.temp_min}°C - {activity.temp_max}°C
        🌧️ **Maximum Rain:** {activity.rain} mm
        💨 **Wind Speed Range:** {activity.wind_min} - {activity.wind_max} km/h
        ⏰ **Time Range:** {activity.time_range[0]} - {activity.time_range[1]}
        """
        
        panel = Panel(
            Markdown(activity_info),
            title="Activity Details",
            border_style="green"
        )
        console.print(panel)
        
    except CLIWeatherException as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# Configuration commands
@config_app.command("clear-cache")
def clear_cache():
    """Clear weather data cache."""
    try:
        weather_service.clear_cache()
        console.print("[green]✅ Cache cleared successfully[/green]")
        
    except CLIWeatherException as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@config_app.command("clear-logs")
def clear_logs():
    """Clear application logs."""
    try:
        weather_service.clear_logs()
        console.print("[green]✅ Logs cleared successfully[/green]")
        
    except CLIWeatherException as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# Main command for backwards compatibility
@app.command("interactive")
def run_interactive():
    """Launch interactive Rich UI mode."""
    try:
        from .rich_ui import RichUI
        rich_ui = RichUI()
        rich_ui.run()
    except ImportError:
        console.print("[red]Rich UI not available. Install rich package.[/red]")
        raise typer.Exit(1)


class TyperCLI:
    """Wrapper class for the Typer CLI application."""
    
    def __init__(self):
        self.app = app
    
    def run(self, args: Optional[List[str]] = None):
        """Run the Typer CLI with optional arguments."""
        if args is None:
            args = sys.argv[1:]
        
        try:
            self.app(args)
        except typer.Exit as e:
            sys.exit(e.exit_code)
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            logger.exception(f"Unexpected error in CLI: {e}")
            sys.exit(1)


# Entry point for direct CLI usage
if __name__ == "__main__":
    app()
