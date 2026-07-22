from __future__ import annotations

from time import perf_counter

import cv2
from kivy import platform
from kivy.factory import Factory
from kivy.graphics.texture import Texture
from kivy.properties import BooleanProperty
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

DEFAULT_RESOLUTION = (1920, 1080)
RESOLUTION_CANDIDATES = (DEFAULT_RESOLUTION, (1280, 720), (640, 480))


class CameraPreview(Image):
    """Live camera preview with optional sudoku contour highlight.

    Subclasses open a single capture backend via ``_open_capture`` /
    ``_close_capture``. Shared preview, detection, and texture logic lives here.
    """

    play = BooleanProperty(False)

    def __init__(self, **kwargs):
        self.success_img = None
        self.success_contour = None
        self._last_contour = None
        self._next_detect_at = 0.0
        self._preview_texture: Texture | None = None
        kwargs = dict(kwargs)
        kwargs.pop("play", None)
        super().__init__(**kwargs)
        self.play = False

    def start_capture(self):
        """Start capture via the subclass backend."""
        self.stop_capture()
        self._open_capture()
        self.toggle_capture_button(False)

    def stop_capture(self):
        """Release the backend and clear shared preview / detection state."""
        self.success_img = None
        self.success_contour = None
        self.play = False
        self._last_contour = None
        self._next_detect_at = 0.0
        self._preview_texture = None
        self._close_capture()

    def _open_capture(self) -> None:
        raise NotImplementedError

    def _close_capture(self) -> None:
        raise NotImplementedError

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

        self.toggle_capture_button(self.success_img is not None)

        if now >= self._next_detect_at:
            self._next_detect_at = now + _DETECT_INTERVAL_S
            self._last_contour = find_sudoku_quad(frame_rgba)

            if self._last_contour is not None:
                self.success_img = frame_rgba
                self.success_contour = self._last_contour

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

    def toggle_capture_button(self, enabled: bool) -> None:
        camera_screen = get_app().sm.get_screen("camera")  # pyright: ignore[reportOptionalMemberAccess]
        capture_button = camera_screen.ids.capture_sudoku_button
        capture_button.disabled = not enabled


def get_camera_preview_class() -> type[CameraPreview]:
    """Return the platform-specific preview widget class."""

    # import the platform-specific classes here to avoid circular imports
    if platform == "android":
        from widgets.native_camera_preview import NativeCameraPreview

        return NativeCameraPreview

    from widgets.ip_webcam_preview import IpWebcamPreview

    return IpWebcamPreview


# KV uses ``CameraPreview``; map that name to the live backend for this platform.
Factory.unregister("CameraPreview")
Factory.register("CameraPreview", cls=get_camera_preview_class())
