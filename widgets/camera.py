from __future__ import annotations

from time import perf_counter

import cv2
import numpy as np
from kivy import platform
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.logger import Logger
from kivy.properties import BooleanProperty, ObjectProperty
from kivy.uix.image import Image

from app.utils import get_app
from core.vision import draw_contours, find_sudoku_contour

# Contour detection rate; preview still updates every frame using the last contour.
_DETECT_INTERVAL_S = 1 / 10


class KivyCamera(Image):
    """Live camera preview with optional sudoku contour highlight.

    - Android: native device camera (Kivy CoreCamera)
    - Linux/desktop: IP webcam URL via OpenCV VideoCapture
    """

    play = BooleanProperty(False)
    index = ObjectProperty(0)
    resolution = ObjectProperty((1280, 720))

    def __init__(self, **kwargs):
        self.img = None
        self._camera = None
        self._cap = None
        self._clock_ev = None
        self._last_contour = None
        self._next_detect_at = 0.0
        kwargs = dict(kwargs)
        kwargs.pop("play", None)
        index = kwargs.pop("index", 0)
        resolution = kwargs.pop("resolution", (1920, 1080))
        super().__init__(**kwargs)
        self.index = index if index != -1 else 0
        self.resolution = resolution
        self.play = False

    def start_capture(self):
        self.stop_capture()
        if platform == "android":
            self._start_device_camera()
        else:
            self._start_ip_webcam()

    def stop_capture(self):
        self.play = False
        self._last_contour = None
        self._next_detect_at = 0.0
        if self._clock_ev is not None:
            self._clock_ev.cancel()
            self._clock_ev = None
        if self._camera is not None:
            try:
                self._camera.stop()
            except Exception:
                pass
            self._camera = None
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

    def _start_device_camera(self):
        from kivy.core.camera import Camera as CoreCamera

        if self.index < 0:
            return

        # Android Camera.setPreviewSize only accepts supported sizes; portrait
        # dims like 720x1280 typically fail with setParameters.
        candidates = []
        if self.resolution and self.resolution[0] > 0 and self.resolution[1] > 0:
            candidates.append(tuple(self.resolution))
        for size in ((1280, 720), (1920, 1080), (640, 480)):
            if size not in candidates:
                candidates.append(size)

        last_exc = None
        for width, height in candidates:
            try:
                self._camera = CoreCamera(
                    index=self.index,
                    resolution=(width, height),
                    stopped=True,
                )
                self._camera.bind(on_texture=self._on_device_tex)
                self._camera.start()
                self.resolution = (width, height)
                self.play = True
                Logger.info(
                    "Camera: opened device %s at %sx%s", self.index, width, height
                )
                return
            except Exception as exc:
                last_exc = exc
                Logger.warning("Camera: open failed at %sx%s (%s)", width, height, exc)
                self._camera = None

        Logger.warning("Camera: device open failed (%s)", last_exc)

    def _start_ip_webcam(self):
        url = get_app().camera_url
        Logger.info("Camera: opening IP webcam %s", url)
        self._cap = cv2.VideoCapture(url)
        if not self._cap.isOpened():
            Logger.warning("Camera: failed to open IP webcam %s", url)
            self._cap = None
            return
        self.play = True
        self._clock_ev = Clock.schedule_interval(self._on_ip_frame, 1 / 30)

    def _process_frame_rgba(self, frame_rgba):
        now = perf_counter()
        if now >= self._next_detect_at:
            self._next_detect_at = now + _DETECT_INTERVAL_S
            self._last_contour = find_sudoku_contour(frame_rgba)
            if self._last_contour is not None:
                self.img = frame_rgba

        if self._last_contour is not None:
            frame_with_highlight = frame_rgba.copy()
            draw_contours(
                frame_with_highlight,
                [self._last_contour],
                color=(255, 255, 0, 255),
                thickness=2,
            )
        else:
            frame_with_highlight = frame_rgba

        buf = cv2.flip(frame_with_highlight, 1).tobytes()
        image_texture = Texture.create(
            size=(frame_with_highlight.shape[1], frame_with_highlight.shape[0]),
            colorfmt="rgba",
        )
        image_texture.blit_buffer(buf, colorfmt="rgba", bufferfmt="ubyte")
        self.texture = image_texture
        self.texture_size = list(image_texture.size)

    def _on_device_tex(self, camera):
        if camera.texture is None:
            return
        try:
            height, width = camera.texture.height, camera.texture.width
            pixels = np.frombuffer(camera.texture.pixels, np.uint8)
            frame = pixels.reshape(height, width, 4)
            frame = cv2.flip(frame, 0)
            self._process_frame_rgba(frame)
        except Exception as exc:
            Logger.warning("Camera: device frame update failed (%s)", exc)

    def _on_ip_frame(self, _dt):
        if self._cap is None or not self._cap.isOpened():
            return False
        ret, frame_bgr = self._cap.read()
        if not ret or frame_bgr is None:
            return
        try:
            # Uncomment when using IP Webcam portrait mode
            # frame_bgr = cv2.rotate(frame_bgr, cv2.ROTATE_90_ANTICLOCKWISE)
            frame_rgba = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGBA)
            self._process_frame_rgba(frame_rgba)
        except Exception as exc:
            Logger.warning("Camera: IP frame update failed (%s)", exc)
