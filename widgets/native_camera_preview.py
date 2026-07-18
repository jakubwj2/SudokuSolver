from __future__ import annotations

import cv2
import numpy as np
from kivy.logger import Logger
from kivy.properties import ObjectProperty

from widgets.camera import DEFAULT_RESOLUTION, RESOLUTION_CANDIDATES, CameraPreview


class NativeCameraPreview(CameraPreview):
    """Android / native device camera via Kivy CoreCamera."""

    index: int = ObjectProperty(0)
    resolution: tuple[int, int] = ObjectProperty(DEFAULT_RESOLUTION)

    def __init__(self, **kwargs):
        self._camera = None
        kwargs = dict(kwargs)
        index = kwargs.pop("index", 0)
        resolution = kwargs.pop("resolution", DEFAULT_RESOLUTION)
        super().__init__(**kwargs)
        self.index = index if index != -1 else 0
        self.resolution = resolution

    def _open_capture(self) -> None:
        from kivy.core.camera import Camera as CoreCamera

        if self.index < 0:
            return

        # Android Camera.setPreviewSize only accepts supported sizes; portrait
        # dims like 720x1280 typically fail with setParameters.
        candidates: list[tuple[int, int]] = []
        if self.resolution and self.resolution[0] > 0 and self.resolution[1] > 0:
            candidates.append(tuple(self.resolution))  # type: ignore
        for size in RESOLUTION_CANDIDATES:
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

    def _close_capture(self) -> None:
        if self._camera is not None:
            try:
                self._camera.stop()
            except Exception:
                pass
            self._camera = None

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
