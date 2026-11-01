import sys
from unittest.mock import patch

import cli_weather.__main__ as entrypoint


def run_with_args(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", ["cli-weather", *args])
    with (
        patch.object(entrypoint, "run_tui") as tui,
        patch.object(entrypoint, "run_rich_ui") as rich,
        patch.object(entrypoint, "run_typer_cli") as typer_cli,
        patch.object(entrypoint, "run_legacy_ui") as legacy,
    ):
        entrypoint.main()
    return tui, rich, typer_cli, legacy


def test_no_args_runs_tui(monkeypatch):
    tui, rich, typer_cli, legacy = run_with_args(monkeypatch, [])
    tui.assert_called_once()
    rich.assert_not_called()
    typer_cli.assert_not_called()
    legacy.assert_not_called()


def test_tui_flag(monkeypatch):
    tui, *_ = run_with_args(monkeypatch, ["--tui"])
    tui.assert_called_once()


def test_rich_flag(monkeypatch):
    _, rich, *_ = run_with_args(monkeypatch, ["--rich"])
    rich.assert_called_once()


def test_legacy_flag(monkeypatch):
    *_, legacy = run_with_args(monkeypatch, ["--legacy"])
    legacy.assert_called_once()


def test_cli_flag_runs_typer(monkeypatch):
    _, _, typer_cli, _ = run_with_args(monkeypatch, ["--cli"])
    typer_cli.assert_called_once_with([])


def test_known_command_runs_typer(monkeypatch):
    _, _, typer_cli, _ = run_with_args(monkeypatch, ["weather", "current"])
    typer_cli.assert_called_once_with(["weather", "current"])


def test_legacy_ui_module_imports():
    import cli_weather.legacy.legacy_main  # noqa: F401
