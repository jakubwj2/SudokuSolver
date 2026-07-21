from __future__ import annotations

import os

import numpy as np
from kivy import platform
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
from widgets.operation_button import OperationButton, ToggleOperationButton
from widgets.sudoku_widget import SudokuCell


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
        self.hide_candidates = True
        self.sudoku_cells: list[SudokuCell] = []
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
        self.sudoku_cells = list(ToggleButtonBehavior.get_widgets("sudoku_cells"))
        if not self.sudoku_cells:
            Logger.warning("SudokuApp: no sudoku cells found at start")
            return
        self.refresh_sudoku()

    def on_stop(self):
        if hasattr(self, "buttons"):
            del self.sudoku_cells
        if self.sm is not None:
            camera_screen = self.sm.get_screen("camera")
            camera_screen.my_camera.stop_capture()

    def load_captured_sudoku(self, new_sudoku: np.ndarray) -> None:
        """Replace the puzzle from a camera capture and show the grid screen."""
        self.table = Table(new_sudoku)
        self.table.given_sudoku = np.zeros((9, 9), dtype=np.int8)
        self.refresh_sudoku()
        if self.sm is not None:
            self.sm.current = "sudoku"

    def repopulate_sudoku(self):
        for cell, number, given_cell_number in zip(
            self.sudoku_cells,
            self.table.sudoku_array.flatten(),
            self.table.given_sudoku.flatten(),
        ):
            cell.number = int(number)
            cell.locked = given_cell_number != 0
        self.populate_candidates(self.hide_candidates)

    def on_solve(self, instance: ToggleOperationButton):
        if self.table.is_solved():
            self.table.reset()
            instance.toggled = False
        else:
            self.table.solve()
            if len(self.table.solutions) != 1:
                instance.toggled = False
                print(
                    "Invalid sudoku (solutions found: %d)" % len(self.table.solutions)
                )
            else:
                instance.toggled = True

        self.refresh_sudoku()

    def on_lock(self, instance: ToggleOperationButton):
        if self.table.is_locked() or self.table.is_empty():
            instance.toggled = False
            self.table.reset_given_sudoku()
        else:
            instance.toggled = True
            self.table.set_given_sudoku()

        self.refresh_sudoku()

    # def on_filter(self, instance: OperationButton):
    #     self.table.filter_candidates()
    #     self.highlight_valid_cells_for_number(
    #         None if self.selected_number is None else self.selected_number.number
    #     )
    #     self.deselect_cell()

    def on_clear(self, _instance):
        if self.selected_cell is not None:
            x, y = self.selected_cell.idx
            if self.table.given_sudoku[x, y] == 0:
                self.table.sudoku_array[x, y] = 0
                self.sudoku_cells[x * 9 + y].number = 0
                return

        def clear_all(_instance: OperationButton):
            self.table = Table()
            self.refresh_sudoku()

        popup = ConfirmPopup(
            on_ok=clear_all,
            text="Clear all cells and reset the sudoku.",
            ok_text="Clear cells",
        )
        popup.open()

    def on_select_number(self, instance: DialButton):
        if instance.state == "normal":
            self.selected_number = None
            self.highlight_valid_cells_for_number(None)
        else:
            self.selected_number = instance
            self.highlight_valid_cells_for_number(self.selected_number.number)

            cell_dial = self.try_get_cell_and_dial()
            if cell_dial:
                self.place_number(*cell_dial)
                self.deselect_number()

    def on_select_cell(self, instance: SudokuCell):
        if instance.locked:
            instance.state = "normal"
            self.deselect_cell()
            return
        if instance.state == "normal":
            self.selected_cell = None
            return

        self.selected_cell = instance

        cell_dial = self.try_get_cell_and_dial()
        if cell_dial:
            self.place_number(*cell_dial)
            self.deselect_cell()

    def on_show_candidates(self, instance: ToggleOperationButton):
        self.hide_candidates = not self.hide_candidates
        instance.toggled = not self.hide_candidates
        self.populate_candidates(self.hide_candidates)

    def populate_candidates(self, hide: bool):
        for cell, candidates in zip(self.sudoku_cells, self.table.candidates.flatten()):
            cell.set_candidates(candidates, hide)

    def place_number(self, cell: SudokuCell, dial: DialButton) -> None:

        x, y = cell.idx
        if self.table.sudoku_array[x, y] == dial.number:
            self.table.remove_number(x, y)
            cell.number = 0
            self.highlight_cells_and_populate_candidates()
            return

        self.table.insert_number(dial.number, x, y)
        cell.number = dial.number

        self.highlight_cells_and_populate_candidates()

    def try_get_cell_and_dial(self) -> tuple[SudokuCell, DialButton] | None:
        if self.selected_number is None or self.selected_cell is None:
            return None
        return self.selected_cell, self.selected_number

    def highlight_cells_and_populate_candidates(self):

        number = self.selected_number.number if self.selected_number else None
        if not number and self.selected_cell:
            number = self.selected_cell.number

        self.highlight_valid_cells_for_number(number)
        self.highlight_errors()
        self.populate_candidates(self.hide_candidates)

    def highlight_valid_cells_for_number(self, number: int | None):
        for cell, placeable in zip(
            self.sudoku_cells, self.table.get_valid_cells_for_number(number)
        ):
            cell.highlight = placeable

    def highlight_errors(self):
        for cell, is_error in zip(self.sudoku_cells, self.table.get_errors()):
            cell.error = is_error

    def deselect_cell(self):
        if self.selected_cell is not None:
            self.selected_cell.state = "normal"
            self.selected_cell = None

    def deselect_number(self):
        if self.selected_number is not None:
            self.selected_number.state = "normal"
            self.selected_number = None

    def refresh_sudoku(self):
        """Refresh the sudoku display to reflect the current state of the table. Refreshes:
        - the sudoku cell numbers and locked status
        - the highlights
        - deselects the cell and dial digits
        - populates the candidates
        """
        self.repopulate_sudoku()
        self.deselect_cell()
        self.deselect_number()
        self.highlight_cells_and_populate_candidates()
