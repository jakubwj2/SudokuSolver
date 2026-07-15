from __future__ import annotations

from kivy.properties import ObjectProperty
from kivy.uix.gridlayout import GridLayout
from kivy.uix.togglebutton import ToggleButton

from app.utils import get_app


class DialWidget(GridLayout):
    """Number pad for placing digits 1–9."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for i in range(9):
            self.add_widget(
                DialButton(
                    number=i + 1,
                    on_press=lambda x: get_app().on_select_number(x),
                )
            )


class DialButton(ToggleButton):
    """A digit button on the dial."""

    number: int = ObjectProperty(int)
