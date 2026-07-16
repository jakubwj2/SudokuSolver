from __future__ import annotations

from pathlib import Path

from kivy import platform
from kivy.core.window import Window
from kivy.lang import Builder

# Register widget/screen classes with the Factory before loading KV.
import screens  # noqa: F401
import widgets  # noqa: F401
from app.sudoku_app import SudokuApp

Builder.load_file(str(Path(__file__).resolve().parent / "kv" / "main.kv"))


if __name__ == "__main__":
    # Poco 6 window size -> (2712, 1220)
    if platform in ("win", "linux"):
        Window.size = (2712 / 3, 1220 / 3)

    SudokuApp().run()
