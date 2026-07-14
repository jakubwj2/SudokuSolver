from kivy.app import App
from kivy.uix.behaviors.togglebutton import ToggleButtonBehavior
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty
from kivy.core.window import Window
from kivy import platform
from kivy.graphics.texture import Texture
from kivy.logger import Logger
import numpy as np
import cv2

from itertools import product

from computer_vision import read_sudoku, try_draw_sudoku_highlight
import time
import os

from sudoku import Table

t = Table()

# Linux/desktop IP webcam (Android uses the device camera instead).
IP_WEBCAM_URL = "http://192.168.1.226:8080/video"


class SudokuWidget(GridLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sections = [[] for _ in range(3)]
        for x, y in product(range(3), range(3)):
            sections[x].append(GridLayout(cols=3, spacing=1))
            self.add_widget(sections[x][y])

        self.buttons = []
        for x, y in product(range(9), range(9)):
            button = SudokuCell(x, y)
            self.buttons.append(button)
            sections[x // 3][y // 3].add_widget(button)


class SudokuCell(ToggleButtonBehavior, AnchorLayout):
    is_locked = BooleanProperty(True)
    is_highlighted = BooleanProperty(True)
    number = ObjectProperty(int)
    candidate_list = StringProperty("")

    def __init__(self, x, y, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.idx = (x, y)
        self.group = "sudoku_cells"

    def on_state(self, widget, value):
        SudokuApp.inst.on_select_cell(self)


class DialWidget(GridLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for i in range(9):
            self.add_widget(
                DialButton(
                    number=i + 1,
                    on_press=lambda x: SudokuApp.inst.on_select_number(x),
                )
            )


class DialButton(ToggleButton):
    number = ObjectProperty(int)


class ConfirmPopup(Popup):
    text = StringProperty("")

    ok_text = StringProperty("OK")
    cancel_text = StringProperty("Cancel")

    __events__ = ("on_ok", "on_cancel")

    def ok(self):
        self.dispatch("on_ok")
        self.dismiss()

    def cancel(self):
        self.dispatch("on_cancel")
        self.dismiss()

    def on_ok(self):
        pass

    def on_cancel(self):
        pass


class SudokuScreen(Screen):
    pass


class KivyCamera(Image):
    """Preview + capture.

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
        url = getattr(SudokuApp.inst, "camera_url", None) or IP_WEBCAM_URL
        Logger.info("Camera: opening IP webcam %s", url)
        self._cap = cv2.VideoCapture(url)
        if not self._cap.isOpened():
            Logger.warning("Camera: failed to open IP webcam %s", url)
            self._cap = None
            return
        self.play = True
        self._clock_ev = Clock.schedule_interval(self._on_ip_frame, 1 / 30)

    def _process_frame_rgba(self, frame_rgba):
        ret, frame_with_highlight = try_draw_sudoku_highlight(frame_rgba.copy())
        if ret:
            self.img = frame_rgba

        buf = cv2.flip(frame_with_highlight, 1).tobytes()
        image_texture = Texture.create(
            size=(frame_with_highlight.shape[1], frame_with_highlight.shape[0]),
            colorfmt="rgba",
        )
        image_texture.blit_buffer(buf, colorfmt="rgba", bufferfmt="ubyte")
        self.texture = image_texture
        self.texture_size = list(image_texture.size)
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


class CameraScreen(Screen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.my_camera = self.ids["camera"]

    def on_enter(self, *args):
        self.my_camera.start_capture()

    def on_leave(self, *args):
        self.my_camera.stop_capture()

    def capture_sudoku(self):
        if self.my_camera.img is None:
            return

        timestr = time.strftime("%Y-%m-%d_%H-%M-%S")
        img_path = os.path.join(SudokuApp.inst.img_folder, "%s.png" % timestr)
        cv2.imwrite(img_path, cv2.cvtColor(self.my_camera.img, cv2.COLOR_RGBA2BGRA))
        new_sudoku = read_sudoku(self.my_camera.img)
        if new_sudoku is None:
            os.rename(img_path, img_path[:-4] + "_None.png")
        else:
            t.__init__(new_sudoku)
            t.original_array = np.zeros((9, 9))
            SudokuApp.inst.repopulate_sudoku()
            SudokuApp.inst.highlight_placeable(None)
            SudokuApp.inst.sm.current = "sudoku"
            SudokuApp.inst.hide_candidates = True
            SudokuApp.inst.populate_candidates(True)


class SudokuApp(App):
    def build(self):
        self.sm = ScreenManager()
        self.sm.add_widget(SudokuScreen())
        self.sm.add_widget(CameraScreen())
        self.sm.current = "sudoku"
        return self.sm

    inst = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        SudokuApp.inst = self

        self.selected_number = None
        self.selected_cell = None
        self.hide_candidates = False
        self.camera_url = IP_WEBCAM_URL

        if platform == "android":
            # Do not defer this to model import — camera preview needs it immediately.
            from android.permissions import request_permissions, Permission

            request_permissions(
                [
                    Permission.CAMERA,
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                ]
            )
            self.img_folder = os.path.join("/sdcard", "DCIM", "SudokuPhotos")
        else:
            self.img_folder = os.path.join(os.getcwd(), "SudokuPhotos")

        if not os.path.exists(self.img_folder):
            os.makedirs(self.img_folder)

    def on_start(self):
        self.buttons = list(ToggleButtonBehavior.get_widgets("sudoku_cells"))
        if not self.buttons:
            Logger.warning("SudokuApp: no sudoku cells found at start")
            return
        self.repopulate_sudoku()
        self.highlight_placeable(None)
        self.populate_candidates(self.hide_candidates)

    def on_stop(self):
        if hasattr(self, "buttons"):
            del self.buttons
        camera_screen = self.sm.get_screen("camera") if self.sm else None
        if camera_screen is not None:
            camera_screen.my_camera.stop_capture()

    def repopulate_sudoku(self):
        for button, number, original in zip(
            self.buttons,
            t.sudoku_array.flatten(),
            t.original_array.flatten(),
        ):
            button.number = number
            button.is_locked = original != 0
            self.populate_candidates(self.hide_candidates)

    def highlight_placeable(self, number):
        for button, placeable in zip(self.buttons, t.get_placeable_cells(number)):
            button.is_highlighted = placeable
        self.populate_candidates(self.hide_candidates)

    def on_solve(self, instance):
        if instance.text == "Solve":
            t.solve()
            instance.text = "Restart"
        else:
            t.reset()
            instance.text = "Solve"
        self.repopulate_sudoku()

        self.highlight_placeable(None)
        self.deselect_cell()
        self.deselect_number()

    def on_lock(self, instance):
        t.original_array = t.sudoku_array
        t.reset()
        self.repopulate_sudoku()

    def on_filter(self, instance):
        t.filter_candidates()
        # t.find_new_values()
        self.highlight_placeable(
            None if self.selected_number is None else self.selected_number.number
        )
        self.deselect_cell()

    def on_clear(self, instance):
        if self.selected_cell is not None:
            x, y = self.selected_cell.idx
            if t.original_array[x, y] == 0:
                t.sudoku_array[x, y] = 0
                self.buttons[x * 9 + y].number = 0
                return

        def clear_all(instance):
            t.__init__()
            self.repopulate_sudoku()
            self.highlight_placeable(None)

        popup = ConfirmPopup(
            on_ok=clear_all,
            text="Clear all cells and reset the sudoku.",
            ok_text="Clear cells",
        )
        popup.open()

    def on_validate(self, instance):
        anim = Animation(
            background_color=(
                (0, 1, 0, 1) if t.validate(t.sudoku_array) else (1, 0, 0, 1)
            ),
            duration=0.1,
        )
        anim += Animation(background_color=instance.background_color, duration=0.1)
        anim.start(instance)

    def on_select_number(self, instance):
        if instance.state == "normal":
            self.selected_number = None
            self.highlight_placeable(None)
        else:
            self.selected_number = instance
            self.highlight_placeable(self.selected_number.number)
            if self.place_number():
                self.deselect_number()

    def on_select_cell(self, instance):
        if instance.is_locked:
            instance.state = "normal"
            self.deselect_cell()
            return
        if instance.state == "normal":
            self.selected_cell = None
            return

        self.selected_cell = instance
        if self.place_number():
            self.deselect_cell()

    def on_show_candidates(self, instance):
        self.hide_candidates = not self.hide_candidates
        self.populate_candidates(self.hide_candidates)

    def populate_candidates(self, hide):
        for button, candidates in zip(self.buttons, t.candidates.flatten()):
            candidate_list = ""
            if candidates is not None and not hide:
                for i in range(1, 10):
                    if i % 3 != 0:
                        candidate_list += f"{i}  " if i in candidates else "   "
                    elif i < 9:
                        candidate_list += f"{i}\n" if i in candidates else " \n"
                    else:
                        candidate_list += str(i) if i in candidates else ""

            button.candidate_list = candidate_list

    def place_number(self) -> bool:
        if self.selected_number is None or self.selected_cell is None:
            return False
        x, y = self.selected_cell.idx
        if t.sudoku_array[x, y] == self.selected_number.number:
            self.on_clear(self.selected_cell)
            self.highlight_placeable(self.selected_number.number)
            return True
        elif not t.place(self.selected_number.number, x, y):
            button = self.buttons[x * 9 + y]
            default_bg_color = button.background_color
            anim = Animation(background_color=(1, 0, 0, 1), duration=0.2)
            anim += Animation(background_color=default_bg_color, duration=0.2)
            anim.start(button)
            self.deselect_cell()
            return False

        self.selected_cell.number = self.selected_number.number
        self.highlight_placeable(self.selected_number.number)
        return True

    def deselect_cell(self):
        if self.selected_cell is not None:
            self.selected_cell.state = "normal"
            self.selected_cell = None

    def deselect_number(self):
        if self.selected_number is not None:
            self.selected_number.state = "normal"
            self.selected_number = None


if __name__ == "__main__":
    # Poco 6 window size -> (2712, 1220)
    if platform in ("win", "linux"):
        Window.size = (2712 / 3, 1220 / 3)

    SudokuApp().run()
