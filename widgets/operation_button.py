from __future__ import annotations

from kivy.properties import StringProperty
from kivy.uix.button import Button


class OperationButton(Button):
    """Toolbar action button (solve, clear, validate, …)."""

    text: str = StringProperty("")
