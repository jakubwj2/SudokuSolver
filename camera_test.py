#! ./.venv/bin/python
from __future__ import annotations

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
import cv2
import numpy as np


class UrlCameraView(BoxLayout):
    """Pull frames from an HTTP/RTSP URL via OpenCV."""

    def __init__(self, url: str, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.url = url
        self.image = Image(fit_mode="contain")
        self.status = Label(size_hint_y=None, height=40, text=f"Connecting:\n{url}")
        self.add_widget(self.image)
        self.add_widget(self.status)

        self.cap = cv2.VideoCapture(url)
        if not self.cap.isOpened():
            self.status.text = f"Failed to open:\n{url}"
            return

        self.status.text = f"Streaming:\n{url}"
        Clock.schedule_interval(self._update, 1 / 30)

    def _update(self, _dt):
        if self.cap is None or not self.cap.isOpened():
            return False
        ret, frame = self.cap.read()
        if not ret or frame is None:
            self.status.text = f"No frame from:\n{self.url}"
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.flipud(frame)
        h, w = frame.shape[:2]
        tex = Texture.create(size=(w, h), colorfmt="rgb")
        tex.blit_buffer(frame.tobytes(), colorfmt="rgb", bufferfmt="ubyte")
        self.image.texture = tex

    def on_parent(self, _instance, parent):
        if parent is None and getattr(self, "cap", None) is not None:
            Clock.unschedule(self._update)
            self.cap.release()
            self.cap = None


class CameraTestApp(App):
    def __init__(self, url: str, **kwargs):
        super().__init__(**kwargs)
        self.stream_url = url

    def build(self):
        return UrlCameraView(self.stream_url)


if __name__ == "__main__":
    url = "http://192.168.1.226:8080/video"
    app = CameraTestApp(url=url)
    app.run()
