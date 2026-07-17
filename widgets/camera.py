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
from core.vision import draw_contours, find_sudoku_quad

# Contour detection rate; preview still updates every frame using the last contour.
_DETECT_INTERVAL_S = 1 / 10

# Preview highlight: outline always; set False to skip the filled blend (cheaper).

_HIGHLIGHT_FILL = platform != "android"
_HIGHLIGHT_FILL_ALPHA = 0.25
_HIGHLIGHT_COLOR = (255, 255, 0, 255)
_HIGHLIGHT_THICKNESS = 2


class KivyCamera(Image):
    """Live camera preview with optional sudoku contour highlight.

    - Android: native device camera (Kivy CoreCamera)
    - Linux/desktop: IP webcam URL via OpenCV VideoCapture

    Attributes:
        img (np.ndarray): The last captured image.
        index (ObjectProperty): The index of the camera to use.
        play (BooleanProperty): Whether the camera is playing.
        resolution (ObjectProperty): The resolution of the camera to use.
        _camera (CoreCamera): The native device camera.
        _cap (cv2.VideoCapture): The IP webcam capture.
        _clock_ev (Clock): The clock event.
        _last_contour (np.ndarray): The last detected contour.
        _next_detect_at (float): The next detect at time.
        _preview_texture (Texture): The preview texture.
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
        self._preview_texture: Texture | None = None
        kwargs = dict(kwargs)
        kwargs.pop("play", None)
        index = kwargs.pop("index", 0)
        resolution = kwargs.pop("resolution", (1920, 1080))
        super().__init__(**kwargs)
        self.index = index if index != -1 else 0
        self.resolution = resolution
        self.play = False

    def start_capture(self):
        """Starts the camera capture. Selects the appropriate camera based on the platform."""
        self.stop_capture()
        if platform == "android":
            self._start_device_camera()
        else:
            self._start_ip_webcam()

    def stop_capture(self):
        """Stops the camera and releases the resources (contours, texture, captures, clocks etc.)."""
        self.play = False
        self._last_contour = None
        self._next_detect_at = 0.0
        self._preview_texture = None
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

    def _ensure_preview_texture(self, width: int, height: int) -> Texture:
        tex = self._preview_texture
        if tex is None or tex.width != width or tex.height != height:
            tex = Texture.create(size=(width, height), colorfmt="rgba")
            self._preview_texture = tex
            self.texture = tex
            self.texture_size = [width, height]
        return tex

    def _process_frame_rgba(self, frame_rgba):
        now = perf_counter()
        if now >= self._next_detect_at:
            self._next_detect_at = now + _DETECT_INTERVAL_S
            self._last_contour = find_sudoku_quad(frame_rgba)
            if self._last_contour is not None:
                self.img = frame_rgba

        if self._last_contour is not None:
            frame_with_highlight = frame_rgba.copy()
            draw_contours(
                frame_with_highlight,
                [self._last_contour],
                color=_HIGHLIGHT_COLOR,
                thickness=_HIGHLIGHT_THICKNESS,
                alpha=_HIGHLIGHT_FILL_ALPHA if _HIGHLIGHT_FILL else 0.0,
            )
        else:
            frame_with_highlight = frame_rgba

        height, width = frame_with_highlight.shape[:2]
        buf = cv2.flip(frame_with_highlight, 1).tobytes()
        tex = self._ensure_preview_texture(width, height)
        tex.blit_buffer(buf, colorfmt="rgba", bufferfmt="ubyte")
        if self.canvas is None:
            return
        self.canvas.ask_update()

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
