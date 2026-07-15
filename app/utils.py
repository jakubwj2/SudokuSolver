from __future__ import annotations

from typing import TYPE_CHECKING, cast

from kivy.app import App

if TYPE_CHECKING:
    from app.sudoku_app import SudokuApp


def get_app() -> SudokuApp:
    """Return the running SudokuApp, or raise if none is active."""
    app = App.get_running_app()
    if app is None:
        raise RuntimeError("App is not running")
    return cast("SudokuApp", app)
