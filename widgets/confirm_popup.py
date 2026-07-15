from __future__ import annotations

from kivy.event import EventDispatcher
from kivy.properties import StringProperty
from kivy.uix.popup import Popup


class ConfirmPopup(Popup):
    """Popup that emits on_ok / on_cancel."""

    text: str = StringProperty("")
    ok_text: str = StringProperty("OK")
    cancel_text: str = StringProperty("Cancel")

    __events__ = ("on_ok", "on_cancel")

    def ok(self):
        EventDispatcher.dispatch(self, "on_ok")
        self.dismiss()

    def cancel(self):
        EventDispatcher.dispatch(self, "on_cancel")
        self.dismiss()

    def on_ok(self):
        pass

    def on_cancel(self):
        pass
