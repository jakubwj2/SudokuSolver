from __future__ import annotations

import os
import time

import cv2
from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen

from app.utils import get_app
from core.ocr import read_sudoku
from widgets.camera import CameraPreview


class CameraScreen(Screen):
    """Camera preview and sudoku capture. Layout lives in kv/main.kv."""

    my_camera: CameraPreview = ObjectProperty(None)

    def on_enter(self, *args):
        self.my_camera.start_capture()

    def on_leave(self, *args):
        self.my_camera.stop_capture()

    def capture_sudoku(self):
        if self.my_camera.success_img is None or self.my_camera.success_contour is None:
            return

        timestr = time.strftime("%Y-%m-%d_%H-%M-%S")
        app = get_app()
        img_path = os.path.join(app.img_folder, "%s.png" % timestr)
        cv2.imwrite(
            img_path, cv2.cvtColor(self.my_camera.success_img, cv2.COLOR_RGBA2BGRA)
        )
        new_sudoku = read_sudoku(
            self.my_camera.success_img, self.my_camera.success_contour
        )
        app.load_captured_sudoku(new_sudoku)
