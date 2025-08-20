"""
Tests for UI implementations.

This module provides basic tests for the Rich and Typer UI implementations
to ensure they can be instantiated and basic functionality works.
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
from io import StringIO
import sys

from cli_weather.core.models import Location
from cli_weather.core.weather_service import WeatherData
from cli_weather.utils import CLIWeatherException


class TestRichUI(unittest.TestCase):
    """Test the Rich UI implementation."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock the WeatherApp to avoid actual initialization
        self.mock_app_patcher = patch('cli_weather.ui.rich_ui.WeatherApp')
        self.mock_app_class = self.mock_app_patcher.start()
        self.mock_app = MagicMock()
        self.mock_app_class.return_value = self.mock_app
        
        # Mock console to capture output
        self.mock_console_patcher = patch('cli_weather.ui.rich_ui.Console')
        self.mock_console_class = self.mock_console_patcher.start()
        self.mock_console = MagicMock()
        self.mock_console_class.return_value = self.mock_console
    
    def tearDown(self):
        """Clean up test environment."""
        self.mock_app_patcher.stop()
        self.mock_console_patcher.stop()
    
    def test_rich_ui_initialization(self):
        """Test that Rich UI can be initialized."""
        from cli_weather.ui.rich_ui import RichUI
        
        ui = RichUI()
        self.assertIsNotNone(ui)
        self.assertEqual(ui.app, self.mock_app)
        self.assertEqual(ui.console, self.mock_console)
    
    @patch('cli_weather.ui.rich_ui.sys.exit')
    def test_show_welcome(self, mock_exit):
        """Test welcome screen display."""
        from cli_weather.ui.rich_ui import RichUI
        
        ui = RichUI()
        ui.show_welcome()
        
        # Verify console.print was called (for welcome message)
        self.assertTrue(self.mock_console.print.called)
    
    def test_display_current_weather(self):
        """Test displaying current weather."""
        from cli_weather.ui.rich_ui import RichUI
        
        ui = RichUI()
        location = Location("Test City", 40.0, -74.0)
        weather = WeatherData("2023-03-15 12:00:00", 20.0, "sunny", 10.0, 0.5)
        
        ui.display_current_weather(location, weather)
        
        # Verify console.print was called to display weather
        self.assertTrue(self.mock_console.print.called)
    
    def test_display_hourly_forecast(self):
        """Test displaying hourly forecast."""
        from cli_weather.ui.rich_ui import RichUI
        
        ui = RichUI()
        location = Location("Test City", 40.0, -74.0)
        forecast = [
            WeatherData("2023-03-15 12:00:00", 20.0, "sunny", 10.0, 0.5),
            WeatherData("2023-03-15 13:00:00", 22.0, "cloudy", 12.0, 0.0),
        ]
        
        ui.display_hourly_forecast(location, forecast)
        
        # Verify console.print was called to display table
        self.assertTrue(self.mock_console.print.called)
    
    def test_display_daily_forecast(self):
        """Test displaying daily forecast."""
        from cli_weather.ui.rich_ui import RichUI
        
        ui = RichUI()
        location = Location("Test City", 40.0, -74.0)
        forecast = [
            WeatherData("2023-03-15", 20.0, "sunny", 10.0, 0.5),
            WeatherData("2023-03-16", 18.0, "rainy", 15.0, 2.5),
        ]
        
        ui.display_daily_forecast(location, forecast)
        
        # Verify console.print was called to display table
        self.assertTrue(self.mock_console.print.called)


class TestTyperCLI(unittest.TestCase):
    """Test the Typer CLI implementation."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock the WeatherApp to avoid actual initialization
        self.mock_app_patcher = patch('cli_weather.ui.typer_cli.WeatherApp')
        self.mock_app_class = self.mock_app_patcher.start()
        self.mock_app = MagicMock()
        self.mock_app_class.return_value = self.mock_app
        
        # Mock console to capture output
        self.mock_console_patcher = patch('cli_weather.ui.typer_cli.Console')
        self.mock_console_class = self.mock_console_patcher.start()
        self.mock_console = MagicMock()
        self.mock_console_class.return_value = self.mock_console
    
    def tearDown(self):
        """Clean up test environment."""
        self.mock_app_patcher.stop()
        self.mock_console_patcher.stop()
    
    def test_typer_cli_initialization(self):
        """Test that Typer CLI can be initialized."""
        from cli_weather.ui.typer_cli import TyperCLI
        
        cli = TyperCLI()
        self.assertIsNotNone(cli)
        self.assertIsNotNone(cli.app)
    
    def test_get_location_by_name_existing(self):
        """Test getting location by name when it exists."""
        from cli_weather.ui.typer_cli import get_location_by_name
        
        # Mock locations
        mock_location = Location("New York", 40.7128, -74.0060)
        self.mock_app.get_locations.return_value = {"New York": mock_location}
        
        result = get_location_by_name("New York")
        
        self.assertEqual(result, mock_location)
    
    def test_get_location_by_name_not_found(self):
        """Test getting location by name when it doesn't exist."""
        from cli_weather.ui.typer_cli import get_location_by_name
        import typer
        
        # Mock empty locations
        self.mock_app.get_locations.return_value = {}
        
        with self.assertRaises(typer.BadParameter):
            get_location_by_name("NonExistent")
    
    def test_get_location_from_args_current(self):
        """Test getting location from args using current location."""
        from cli_weather.ui.typer_cli import get_location_from_args
        
        mock_location = Location("Current", 40.0, -74.0)
        self.mock_app.get_current_location.return_value = mock_location
        
        result = get_location_from_args(current=True)
        
        self.assertEqual(result, mock_location)
        self.mock_app.get_current_location.assert_called_once()
    
    def test_get_location_from_args_coordinates(self):
        """Test getting location from coordinates."""
        from cli_weather.ui.typer_cli import get_location_from_args
        
        mock_location = Location("Custom Location", 40.0, -74.0)
        self.mock_app.create_location_from_coordinates.return_value = mock_location
        
        result = get_location_from_args(latitude=40.0, longitude=-74.0)
        
        self.assertEqual(result, mock_location)
        self.mock_app.create_location_from_coordinates.assert_called_once_with(
            "Custom Location", 40.0, -74.0
        )
    
    def test_get_location_from_args_no_args(self):
        """Test getting location with no valid arguments."""
        from cli_weather.ui.typer_cli import get_location_from_args
        import typer
        
        with self.assertRaises(typer.BadParameter):
            get_location_from_args()
    
    def test_format_weather_table(self):
        """Test formatting weather data as table."""
        from cli_weather.ui.typer_cli import format_weather_table
        
        forecast = [
            WeatherData("2023-03-15", 20.0, "sunny", 10.0, 0.5),
            WeatherData("2023-03-16", 18.0, "rainy", 15.0, 2.5),
        ]
        
        result = format_weather_table(forecast, "Test Forecast")
        
        # Verify it returns a Rich Table object
        from rich.table import Table
        self.assertIsInstance(result, Table)


class TestMainEntry(unittest.TestCase):
    """Test the main entry point functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.original_argv = sys.argv.copy()
    
    def tearDown(self):
        """Clean up test environment."""
        sys.argv = self.original_argv
    
    @patch('cli_weather.__main__.run_rich_ui')
    def test_detect_ui_mode_no_args(self, mock_run_rich):
        """Test UI mode detection with no arguments (should default to Rich)."""
        from cli_weather.__main__ import detect_ui_mode
        
        result = detect_ui_mode(['script_name'])
        
        self.assertEqual(result, 'rich')
    
    @patch('cli_weather.__main__.run_typer_cli')
    def test_detect_ui_mode_with_weather_command(self, mock_run_typer):
        """Test UI mode detection with weather command (should use Typer)."""
        from cli_weather.__main__ import detect_ui_mode
        
        result = detect_ui_mode(['script_name', 'weather', 'current'])
        
        self.assertEqual(result, 'typer')
    
    def test_detect_ui_mode_with_help(self):
        """Test UI mode detection with help argument."""
        from cli_weather.__main__ import detect_ui_mode
        
        result = detect_ui_mode(['script_name', '--help'])
        
        self.assertEqual(result, 'typer')
    
    def test_detect_ui_mode_legacy(self):
        """Test UI mode detection with legacy flag."""
        from cli_weather.__main__ import detect_ui_mode
        
        result = detect_ui_mode(['script_name', '--legacy'])
        
        self.assertEqual(result, 'legacy')
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_show_help(self, mock_stdout):
        """Test help message display."""
        from cli_weather.__main__ import show_help
        
        show_help()
        
        output = mock_stdout.getvalue()
        self.assertIn("CLI Weather Assistant", output)
        self.assertIn("Interactive Modes", output)
        self.assertIn("Command Line Interface", output)


if __name__ == '__main__':
    unittest.main()
