from __future__ import annotations

import os

import numpy as np
from kivy import platform
from kivy.animation import Animation
from kivy.app import App
from kivy.logger import Logger
from kivy.properties import StringProperty
from kivy.uix.behaviors.togglebutton import ToggleButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import ScreenManager

from core.config import get_config
from core.sudoku import Table
from version import __version__
from widgets.confirm_popup import ConfirmPopup
from widgets.dial import DialButton
from widgets.operation_button import OperationButton
from widgets.sudoku_grid import SudokuCell


class RootLayout(FloatLayout):
    """App shell: version chrome in KV; screens added from Python."""

    pass


class SudokuApp(App):
    """Coordinates puzzle state and UI feedback across screens."""

    app_version = StringProperty(__version__)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.table = Table()
        self.selected_number = None
        self.selected_cell = None
        self.hide_candidates = False
        self.buttons: list = []
        self.sm: ScreenManager | None = None

        config = get_config()
        # Linux/desktop IP webcam (Android uses the device camera instead).
        self.camera_url = str(config.camera.ip_webcam_url)

        if platform == "android":
            from android.permissions import (  # pyright: ignore[reportMissingModuleSource]
                Permission,
                request_permissions,
            )

            request_permissions(
                [
                    Permission.CAMERA,
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                ]
            )
            self.img_folder = str(config.paths.photos_dir_android)
        else:
            self.img_folder = str(config.paths.photos_dir)

        if not os.path.exists(self.img_folder):
            os.makedirs(self.img_folder)

    def load_kv(self, filename=None):
        # KV is loaded once from main.py so rules sit under kv/.
        return False

    def build(self):
        # Imported here to avoid a cycle with screens → app.utils.
        from screens.camera_screen import CameraScreen
        from screens.sudoku_screen import SudokuScreen

        root = RootLayout()
        self.sm = ScreenManager()
        self.sm.add_widget(SudokuScreen())
        self.sm.add_widget(CameraScreen())
        self.sm.current = "sudoku"
        # Insert under the KV version label so it stays on top.
        root.add_widget(self.sm, index=len(root.children))
        return root

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
        if self.sm is not None:
            camera_screen = self.sm.get_screen("camera")
            camera_screen.my_camera.stop_capture()

    def load_captured_sudoku(self, new_sudoku: np.ndarray) -> None:
        """Replace the puzzle from a camera capture and show the grid screen."""
        self.table = Table(new_sudoku)
        self.table.original_array = np.zeros((9, 9), dtype=np.int8)
        self.hide_candidates = True
        self.repopulate_sudoku()
        self.highlight_placeable(None)
        self.populate_candidates(True)
        if self.sm is not None:
            self.sm.current = "sudoku"

    def repopulate_sudoku(self):
        for button, number, original in zip(
            self.buttons,
            self.table.sudoku_array.flatten(),
            self.table.original_array.flatten(),
        ):
            button.number = number
            button.is_locked = original != 0
        self.populate_candidates(self.hide_candidates)

    def highlight_placeable(self, number: int | None):
        for button, placeable in zip(
            self.buttons, self.table.get_placeable_cells(number)
        ):
            button.is_highlighted = placeable
        self.populate_candidates(self.hide_candidates)

    def on_solve(self, instance: OperationButton):
        if instance.text == "Solve":
            self.table.solve()
            instance.text = "Restart"
        else:
            self.table.reset()
            instance.text = "Solve"
        self.repopulate_sudoku()
        self.highlight_placeable(None)
        self.deselect_cell()
        self.deselect_number()

    def on_lock(self, instance: OperationButton):
        self.table.original_array = self.table.sudoku_array
        self.table.reset()
        self.repopulate_sudoku()

    def on_filter(self, instance: OperationButton):
        self.table.filter_candidates()
        self.highlight_placeable(
            None if self.selected_number is None else self.selected_number.number
        )
        self.deselect_cell()

    def on_clear(self, _instance):
        if self.selected_cell is not None:
            x, y = self.selected_cell.idx
            if self.table.original_array[x, y] == 0:
                self.table.sudoku_array[x, y] = 0
                self.buttons[x * 9 + y].number = 0
                return

        def clear_all(_instance: OperationButton):
            self.table = Table()
            self.repopulate_sudoku()
            self.highlight_placeable(None)

        popup = ConfirmPopup(
            on_ok=clear_all,
            text="Clear all cells and reset the sudoku.",
            ok_text="Clear cells",
        )
        popup.open()

    def on_validate(self, instance: OperationButton):
        anim = Animation(
            background_color=(
                (0, 1, 0, 1)
                if self.table.validate(self.table.sudoku_array)
                else (1, 0, 0, 1)
            ),
            duration=0.1,
        )
        anim += Animation(background_color=instance.background_color, duration=0.1)
        anim.start(instance)

    def on_select_number(self, instance: DialButton):
        if instance.state == "normal":
            self.selected_number = None
            self.highlight_placeable(None)
        else:
            self.selected_number = instance
            self.highlight_placeable(self.selected_number.number)
            if self.place_number():
                self.deselect_number()

    def on_select_cell(self, instance: SudokuCell):
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

    def on_show_candidates(self, instance: OperationButton):
        self.hide_candidates = not self.hide_candidates
        self.populate_candidates(self.hide_candidates)

    def populate_candidates(self, hide: bool):
        for button, candidates in zip(self.buttons, self.table.candidates.flatten()):
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
        if self.table.sudoku_array[x, y] == self.selected_number.number:
            self.on_clear(self.selected_cell)
            self.highlight_placeable(self.selected_number.number)
            return True
        elif not self.table.place(self.selected_number.number, x, y):
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
