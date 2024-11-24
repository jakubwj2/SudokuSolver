from kivy.app import App
from kivy.uix.behaviors.togglebutton import ToggleButtonBehavior
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.popup import Popup
from kivy.uix.camera import Camera
from kivy.animation import Animation
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty
from kivy.core.window import Window
import numpy as np

from itertools import product

# from computer_vision import read_sudoku
import time
import os

from sudoku import Table

# sudoku = [
#     [0, 0, 7, 9, 3, 0, 0, 0, 8],
#     [6, 8, 0, 0, 0, 5, 0, 9, 0],
#     [0, 0, 0, 0, 0, 0, 0, 0, 2],
#     [0, 0, 0, 4, 0, 0, 0, 8, 0],
#     [5, 0, 0, 1, 0, 6, 0, 3, 0],
#     [0, 6, 0, 0, 0, 0, 0, 0, 0],
#     [0, 0, 1, 0, 5, 4, 0, 0, 0],
#     [0, 0, 9, 7, 0, 0, 0, 0, 1],
#     [0, 0, 0, 0, 0, 0, 0, 7, 0],
# ]

sudoku = [
    [0, 1, 6, 0, 0, 0, 0, 5, 0],
    [0, 3, 0, 1, 0, 0, 0, 4, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 9],
    [0, 0, 1, 0, 0, 3, 5, 0, 0],
    [0, 0, 0, 7, 6, 4, 0, 0, 0],
    [0, 0, 4, 9, 1, 0, 3, 0, 0],
    [1, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 5, 0, 0, 0, 1, 0, 2, 0],
    [0, 4, 0, 0, 5, 0, 8, 0, 0],
]


t = Table(sudoku, empty=" ")


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


# class CameraScreen(Screen):
#     def capture_sudoku(self):
#         camera: Camera = self.ids["camera"]
#         timestr = time.strftime("%Y-%m-%d_%H-%M-%S")
#         img_path = "sudoku_photos/%s.png" % timestr
#         camera.export_to_png(img_path)
#         new_sudoku = read_sudoku(img_path)
#         if new_sudoku is None:
#             os.rename(img_path, img_path[:-4] + "_None.png")
#         else:
#             t.__init__(new_sudoku)
#             t.original_array = np.zeros((9, 9))
#             SudokuApp.inst.repopulate_sudoku()
#             SudokuApp.inst.highlight_placeable(None)
#             SudokuApp.inst.sm.current = "sudoku"
#             SudokuApp.inst.hide_candidates = True
#             SudokuApp.inst.populate_candidates(True)


class SudokuApp(App):

    sm = ScreenManager()

    def build(self):
        self.sm.add_widget(SudokuScreen())
        # self.sm.add_widget(CameraScreen())
        return self.sm

    inst = None

    def __init__(self, **kwargs):
        if SudokuApp.inst is None:
            SudokuApp.inst = self
        else:
            del self
            return
        super().__init__(**kwargs)

        self.selected_number = None
        self.selected_cell = None
        self.hide_candidates = False

    def on_start(self):
        self.buttons = ToggleButtonBehavior.get_widgets("sudoku_cells")
        self.repopulate_sudoku()
        self.highlight_placeable(None)
        self.populate_candidates(self.hide_candidates)

    def on_stop(self):
        del self.buttons

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
            background_color=(0, 1, 0, 1) if t.validate() else (1, 0, 0, 1),
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
    # if platform == "win" or platform == "linux":
    #     Config.set("graphics", "resizable", False)
    # Window.size = (810, 540)
    # Window.size = (2712, 1220)
    Window.size = (2712 / 3, 1220 / 3)
    # Window.size = (1220 / 3, 2712 / 3)

    # Poco 6 window size -> (2712, 1220)
    SudokuApp().run()
