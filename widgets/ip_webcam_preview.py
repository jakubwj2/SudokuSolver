from __future__ import annotations

import cv2
from kivy.clock import Clock
from kivy.logger import Logger

from app.utils import get_app
from widgets.camera import CameraPreview


class IpWebcamPreview(CameraPreview):
    """Desktop IP webcam via OpenCV VideoCapture + Clock."""

    def __init__(self, **kwargs):
        self._cap = None
        self._clock_ev = None
        super().__init__(**kwargs)

    def _open_capture(self) -> None:
        url = get_app().camera_url
        Logger.info("Camera: opening IP webcam %s", url)
        self._cap = cv2.VideoCapture(url)
        if not self._cap.isOpened():
            Logger.warning("Camera: failed to open IP webcam %s", url)
            self._cap = None
            return
        self.play = True
        self._clock_ev = Clock.schedule_interval(self._on_ip_frame, 1 / 30)

    def _close_capture(self) -> None:
        if self._clock_ev is not None:
            self._clock_ev.cancel()
            self._clock_ev = None
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

    def _on_ip_frame(self, _dt):
        if self._cap is None or not self._cap.isOpened():
            return False
        ret, frame_bgr = self._cap.read()
        if not ret or frame_bgr is None:
            return
        try:
            # # Uncomment when using IP Webcam portrait mode
            frame_bgr = cv2.rotate(frame_bgr, cv2.ROTATE_90_CLOCKWISE)
            frame_rgba = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGBA)
            self._process_frame_rgba(frame_rgba)
        except Exception as exc:
            Logger.warning("Camera: IP frame update failed (%s)", exc)
