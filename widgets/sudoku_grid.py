from __future__ import annotations

from collections.abc import Sequence
from itertools import product

from kivy.properties import (
    ColorProperty,
    ObjectProperty,
    OptionProperty,
    StringProperty,
)
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors.togglebutton import ToggleButtonBehavior
from kivy.uix.gridlayout import GridLayout

from app.utils import get_app


class SudokuWidget(GridLayout):
    """Displays a 9x9 Sudoku board as nested 3x3 sections."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sections = [[] for _ in range(3)]
        for x, y in product(range(3), range(3)):
            sections[x].append(GridLayout(cols=3, spacing=1))
            self.add_widget(sections[x][y])

        self.buttons = []
        for x, y in product(range(9), range(9)):
            button = SudokuCell(x, y)
            self.buttons.append(button)
            sections[x // 3][y // 3].add_widget(button)


class SudokuCell(ToggleButtonBehavior, AnchorLayout):  # pyright: ignore[reportIncompatibleMethodOverride]
    """A single selectable cell in the Sudoku grid."""

    status: str = OptionProperty(
        "normal", options=["normal", "locked", "error", "highlight"]
    )
    number: int = ObjectProperty(int)
    candidate_list: str = StringProperty("")
    background_color: ColorProperty = ColorProperty((0, 0, 0, 0))

    def __init__(self, x: int, y: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.idx = (x, y)
        self.group = "sudoku_cells"

    def on_state(self, widget: SudokuCell, value: str):
        get_app().on_select_cell(self)

    def on_status(self, widget: SudokuCell, value: str):
        if value == "normal":
            self.background_color = (0, 0, 0, 0)
        elif value == "locked":
            self.background_color = (1, 1, 1, 1)
        elif value == "error":
            self.background_color = (1, 0, 0, 0.5)
        elif value == "highlight":
            self.background_color = (0, 0, 0.5, 0.5)

    def can_show_candidates(self) -> bool:
        return self.number == 0

    def set_candidates(self, candidates: Sequence[int] | None, hide: bool):
        if hide or not self.can_show_candidates():
            self.candidate_list = ""
            return

        candidate_list = ""
        if candidates is not None:
            for i in range(1, 10):
                if i % 3 != 0:
                    candidate_list += f"{i}  " if i in candidates else "   "
                elif i < 9:
                    candidate_list += f"{i}\n" if i in candidates else " \n"
                else:
                    candidate_list += str(i) if i in candidates else ""

        self.candidate_list = candidate_list
