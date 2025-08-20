"""
UI layer for CLI Weather application.

This package contains different UI implementations for the weather application.
"""

from .rich_ui import RichUI
from .typer_cli import TyperCLI

__all__ = ['RichUI', 'TyperCLI']
