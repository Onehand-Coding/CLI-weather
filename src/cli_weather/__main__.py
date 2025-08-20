#!/usr/bin/env python
"""
Main entry point for the CLI Weather Application.

This module provides the main entry point with support for both Rich interactive UI
and Typer command-line interface modes. It uses the new separated architecture
with core business logic and UI implementations.
"""

import sys
import argparse
import logging

from .legacy.config import configure_logging
from .legacy.utils import CLIWeatherException

logger = logging.getLogger(__name__)


def run_rich_ui():
    """Run the Rich-based interactive UI."""
    try:
        from .ui.rich_ui import RichUI
        ui = RichUI()
        ui.run()
    except ImportError as e:
        print(f"Error: Rich UI not available. {e}")
        print("Please install the 'rich' package: pip install rich")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Error in Rich UI: {e}")
        print(f"Error running Rich UI: {e}")
        sys.exit(1)


def run_typer_cli(args=None):
    """Run the Typer-based command-line interface."""
    try:
        from .ui.typer_cli import TyperCLI
        cli = TyperCLI()
        cli.run(args)
    except ImportError as e:
        print(f"Error: Typer CLI not available. {e}")
        print("Please install the 'typer' package: pip install typer")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Error in Typer CLI: {e}")
        print(f"Error running Typer CLI: {e}")
        sys.exit(1)


def run_legacy_ui():
    """Run the legacy interactive UI for backwards compatibility."""
    try:
        # Import legacy main function
        from .legacy.legacy_main import legacy_main
        legacy_main()
    except ImportError:
        print("Legacy UI not available. Using Rich UI instead.")
        run_rich_ui()
    except Exception as e:
        logger.exception(f"Error in legacy UI: {e}")
        print(f"Error running legacy UI: {e}")
        sys.exit(1)


def detect_ui_mode(args):
    """Detect which UI mode to use based on arguments."""
    # If there are command line arguments (beyond script name), use Typer CLI
    if len(args) > 1:
        # Check if it's a help request or specific command
        if any(arg in ['--help', '-h', 'help'] for arg in args[1:]):
            return 'typer'
        # Check for known Typer commands
        known_commands = ['weather', 'location', 'activity', 'config', 'interactive']
        if len(args) > 1 and args[1] in known_commands:
            return 'typer'
        # Check for legacy mode flag
        if '--legacy' in args or '--old' in args:
            return 'legacy'
        # Default to typer for any other arguments
        return 'typer'
    else:
        # No arguments, default to Rich UI
        return 'rich'


def show_help():
    """Show help message with usage options."""
    help_text = """
CLI Weather Assistant - Usage Options:

🌤️  Interactive Modes:
  cli-weather                    # Launch Rich interactive UI (default)
  cli-weather --legacy          # Launch legacy interactive UI
  cli-weather interactive       # Explicitly launch Rich UI

⚡ Command Line Interface:
  cli-weather weather --help    # Weather commands help
  cli-weather location --help   # Location commands help
  cli-weather activity --help   # Activity commands help
  cli-weather config --help     # Configuration commands help

📖 Examples:
  cli-weather weather current --current
  cli-weather weather daily --location "New York"
  cli-weather location add "Home" --lat 40.7128 --lon -74.0060
  cli-weather activity add "jogging" --temp-min 15 --temp-max 25

🔗 For full command documentation:
  cli-weather --help
"""
    print(help_text)


def main() -> None:
    """Main entry point for the CLI Weather Application."""
    configure_logging()
    logger.debug("CLI Weather application started")
    
    try:
        # Handle special help cases
        if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
            show_help()
            return
        
        # Detect UI mode
        ui_mode = detect_ui_mode(sys.argv)
        
        logger.debug(f"Selected UI mode: {ui_mode}")
        
        # Run appropriate UI
        if ui_mode == 'rich':
            run_rich_ui()
        elif ui_mode == 'typer':
            # Remove script name and pass remaining args
            run_typer_cli(sys.argv[1:])
        elif ui_mode == 'legacy':
            # Remove legacy flag and run legacy UI
            filtered_args = [arg for arg in sys.argv if arg not in ['--legacy', '--old']]
            if len(filtered_args) == 1:  # Only script name remains
                run_legacy_ui()
            else:
                print("Legacy mode only supports interactive UI")
                run_legacy_ui()
        else:
            print(f"Unknown UI mode: {ui_mode}")
            show_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.debug("Application interrupted by user")
        print("\nGoodbye!")
        sys.exit(0)
    except CLIWeatherException as e:
        logger.error(f"CLI Weather error: {e}")
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
