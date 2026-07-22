from __future__ import annotations

from kivy.animation import Animation
from kivy.properties import BooleanProperty, ColorProperty, StringProperty
from kivy.uix.button import Button


class OperationButton(Button):
    """Toolbar action button (solve, clear, validate, …)."""

    text: str = StringProperty("")
    icon_source: str = StringProperty("")
    image_color: list[float] = ColorProperty(None)

    def flash_error(self):
        anim = Animation(background_color=(1, 0, 0, 1), duration=0.25)
        anim += Animation(background_color=self.background_color, duration=0.25)
        anim.start(self)


class ToggleOperationButton(OperationButton):
    """Toolbar action button that swaps icons when toggled."""

    default_icon_source: str = StringProperty("")
    toggled_icon_source: str = StringProperty("")
    toggled: bool = BooleanProperty(False)
