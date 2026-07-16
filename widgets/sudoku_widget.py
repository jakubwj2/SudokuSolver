from __future__ import annotations

from collections.abc import Sequence
from itertools import product

from kivy.properties import (
    BooleanProperty,
    ColorProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors.togglebutton import ToggleButtonBehavior
from kivy.uix.gridlayout import GridLayout
from kivy.utils import get_color_from_hex

from app.utils import get_app
from core.sudoku import CELL_COORDS

Color = tuple[float, float, float, float]


class SudokuWidget(GridLayout):
    """Displays a 9x9 Sudoku board as nested 3x3 sections."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sections = [[] for _ in range(3)]
        for x, y in product(range(3), range(3)):
            sections[x].append(GridLayout(cols=3, spacing=1))
            self.add_widget(sections[x][y])

        self.buttons = []
        for x, y in CELL_COORDS:
            button = SudokuCell(x, y)
            self.buttons.append(button)
            sections[x // 3][y // 3].add_widget(button)


class SudokuCell(ToggleButtonBehavior, AnchorLayout):  # pyright: ignore[reportIncompatibleMethodOverride]
    """A single selectable cell in the Sudoku grid."""

    locked: bool = BooleanProperty(False)
    error: bool = BooleanProperty(False)
    highlight: bool = BooleanProperty(False)

    BASE: Color = (0, 0, 0, 0)
    HIGHLIGHT: Color = (0, 0, 0.5, 0.5)
    ERROR: Color = (1, 0, 0, 0.5)
    LOCKED: Color = (1, 1, 1, 1)
    SELECT: Color = (0, 0, 1, 0.5)

    TEXT_BASE = get_color_from_hex("#08313a")
    TEXT_LOCKED: Color = (0, 0, 0, 1)
    TEXT_ERROR: Color = (1, 0, 0, 1)

    number: int = ObjectProperty(int)
    candidate_list: str = StringProperty("")
    text_color: ColorProperty = ColorProperty(TEXT_BASE)
    background_color: ColorProperty = ColorProperty(BASE)

    def __init__(self, x: int, y: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.idx = (x, y)
        self.group = "sudoku_cells"

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

    def on_state(self, widget: SudokuCell, value: str):
        get_app().on_select_cell(self)
        self._refresh_style()

    def on_locked(self, widget: SudokuCell, value: bool):
        self._refresh_style()

    def on_error(self, widget: SudokuCell, value: bool):
        self._refresh_style()

    def on_highlight(self, widget: SudokuCell, value: bool):
        self._refresh_style()

    def on_number(self, widget: SudokuCell, value: int):
        self._refresh_style()

    def _refresh_style(self):

        bg = self.BASE

        if self.highlight:
            bg = blend(bg, self.HIGHLIGHT)
        if self.state == "down":
            bg = blend(bg, self.SELECT)
        if self.error:
            bg = blend(bg, self.ERROR)
        if self.locked:
            bg = blend(bg, self.LOCKED)

        if self.error:
            text_color = self.TEXT_ERROR
        elif self.locked:
            text_color = self.TEXT_LOCKED
        else:
            text_color = self.TEXT_BASE

        self.background_color = bg
        self.text_color = text_color


def blend(bg: Color, fg: Color) -> Color:
    fg_alpha_inv = 1 - fg[3]
    return (
        bg[0] * fg_alpha_inv + fg[0] * fg[3],
        bg[1] * fg_alpha_inv + fg[1] * fg[3],
        bg[2] * fg_alpha_inv + fg[2] * fg[3],
        bg[3] + fg[3],
    )
