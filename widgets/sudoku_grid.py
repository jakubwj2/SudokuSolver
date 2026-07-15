from __future__ import annotations

from itertools import product

from kivy.properties import BooleanProperty, ObjectProperty, StringProperty
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

    is_locked: bool = BooleanProperty(True)
    is_highlighted: bool = BooleanProperty(True)
    number: int = ObjectProperty(int)
    candidate_list: str = StringProperty("")

    def __init__(self, x: int, y: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.idx = (x, y)
        self.group = "sudoku_cells"

    def on_state(self, widget: SudokuCell, value: str):
        get_app().on_select_cell(self)
