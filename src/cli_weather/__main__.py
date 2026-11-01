#!/usr/bin/env python
"""
Main entry point for the CLI Weather Application.

This module provides the main entry point with support for both Rich interactive UI
and Typer command-line interface modes. It uses the new separated architecture
with core business logic and UI implementations.
"""

import logging
import sys

from .legacy.config import configure_logging
from .legacy.utils import CLIWeatherException

logger = logging.getLogger(__name__)


def run_tui():
    """Run the Textual TUI."""
    try:
        from .ui.tui import run as run_tui_app

        run_tui_app()
    except ImportError as e:
        print(f"Error: TUI not available. {e}")
        print("Please install the 'textual' package: pip install textual")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Error in TUI: {e}")
        print(f"Error running TUI: {e}")
        sys.exit(1)


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
    if len(args) <= 1:
        return "tui"
    if "--tui" in args:
        return "tui"
    if "--rich" in args:
        return "rich"
    if "--legacy" in args or "--old" in args:
        return "legacy"
    if "--cli" in args or any(arg in ["--help", "-h", "help"] for arg in args[1:]):
        return "typer"
    known_commands = ["weather", "location", "activity", "config"]
    if args[1] in known_commands:
        return "typer"
    return "typer"


def show_help():
    """Show help message with usage options."""
    help_text = """
CLI Weather Assistant - Usage Options:

🌤️  Interfaces:
  cli-weather                    # Launch the Textual TUI (default)
  cli-weather --tui              # Explicitly launch the TUI
  cli-weather --rich             # Launch the Rich interactive UI
  cli-weather --legacy           # Launch the legacy UI

⚡ Command Line Interface:
  cli-weather --cli weather --help
  cli-weather weather current --current
  cli-weather location list
  cli-weather activity list

Configuration is stored at ~/.config/cli-weather/config.json.
Set CLI_WEATHER_CONFIG_DIR to override the location.
"""
    print(help_text)


def main() -> None:
    """Main entry point for the CLI Weather Application."""
    configure_logging()
    logger.debug("CLI Weather application started")

    try:
        # Handle special help cases
        if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h", "help"]:
            show_help()
            return

        # Detect UI mode
        ui_mode = detect_ui_mode(sys.argv)

        logger.debug(f"Selected UI mode: {ui_mode}")

        # Run appropriate UI
        if ui_mode == "tui":
            run_tui()
        elif ui_mode == "rich":
            run_rich_ui()
        elif ui_mode == "typer":
            args = [arg for arg in sys.argv[1:] if arg != "--cli"]
            run_typer_cli(args)
        elif ui_mode == "legacy":
            # Remove legacy flag and run legacy UI
            filtered_args = [
                arg for arg in sys.argv if arg not in ["--legacy", "--old"]
            ]
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
