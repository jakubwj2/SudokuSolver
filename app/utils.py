from __future__ import annotations

from typing import TYPE_CHECKING, cast

from kivy.app import App

from typings.color import Color

if TYPE_CHECKING:
    from app.sudoku_app import SudokuApp


def get_app() -> SudokuApp:
    """Return the running SudokuApp, or raise if none is active."""
    app = App.get_running_app()
    if app is None:
        raise RuntimeError("App is not running")
    return cast("SudokuApp", app)


def blend(bg: Color, fg: Color) -> Color:
    fg_alpha_inv = 1 - fg[3]
    return (
        bg[0] * fg_alpha_inv + fg[0] * fg[3],
        bg[1] * fg_alpha_inv + fg[1] * fg[3],
        bg[2] * fg_alpha_inv + fg[2] * fg[3],
        bg[3] + fg[3],
    )
