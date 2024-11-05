from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.config import Config
from kivy.utils import platform
from kivy.uix.popup import Popup
from kivy.properties import StringProperty, BooleanProperty
from kivy.lang.builder import Builder
from kivy.core.window import Window

# from kivy.clock import Clock
from kivy.animation import Animation

from sudoku import Table
from itertools import product

sudoku = [
    [0, 0, 7, 9, 3, 0, 0, 0, 8],
    [6, 8, 0, 0, 0, 5, 0, 9, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 2],
    [0, 0, 0, 4, 0, 0, 0, 8, 0],
    [5, 0, 0, 1, 0, 6, 0, 3, 0],
    [0, 6, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 0, 5, 4, 0, 0, 0],
    [0, 0, 9, 7, 0, 0, 0, 0, 1],
    [0, 0, 0, 0, 0, 0, 0, 7, 0],
]

t = Table(sudoku, empty=" ")

Builder.load_file("Sudoku.kv")


class SudokuWidget(GridLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sections: list[list[GridLayout]] = [[] for _ in range(3)]
        for x, y in product(range(3), range(3)):
            self.sections[x].append(GridLayout(cols=3, spacing=1))
            self.add_widget(self.sections[x][y])

        self.buttons = []
        for x, y in product(range(9), range(9)):
            button = SudokuCell(x, y, on_press=SudokuApp.inst.on_select_cell)
            self.buttons.append(button)
            self.sections[x // 3][y // 3].add_widget(button)


class SudokuCell(ToggleButton):
    is_locked = BooleanProperty(True)
    is_highlighted = BooleanProperty(True)

    def __init__(self, x, y, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.idx = x, y


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
    def __init__(self, number, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.number = number
        self.text = str(number)


class OperationButton(Button):
    pass


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


class MainLayout(BoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sudoku_widget = SudokuWidget()

        anchor = AnchorLayout(
            anchor_x="left", anchor_y="top", size_hint=(None, 1), size=(1100, 0)
        )
        anchor.add_widget(self.sudoku_widget)
        self.add_widget(anchor)

        vertical = BoxLayout(orientation="vertical", spacing=20)

        dial_anchor_layout = AnchorLayout(
            anchor_x="center",
            anchor_y="top",
        )
        dial_anchor_layout.add_widget(DialWidget())
        vertical.add_widget(dial_anchor_layout)

        operation_buttons = BoxLayout(orientation="vertical", spacing=40)

        operation_buttons.add_widget(
            OperationButton(text="Clear", on_press=SudokuApp.inst.on_clear)
        )
        operation_buttons.add_widget(
            OperationButton(text="Lock", on_press=SudokuApp.inst.on_lock)
        )
        operation_buttons.add_widget(
            OperationButton(text="Validate", on_press=SudokuApp.inst.on_validate)
        )
        operation_buttons.add_widget(
            OperationButton(text="Solve", on_press=SudokuApp.inst.on_solve)
        )

        vertical.add_widget(operation_buttons)

        self.add_widget(vertical)


class SudokuApp(App):
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

    def build(self):
        self.main_layout = MainLayout()
        self.buttons = self.main_layout.sudoku_widget.buttons
        return self.main_layout

    def on_start(self):
        self.repopulate_sudoku()
        self.highlight_placeable(None)

        # self.update_event = Clock.schedule_interval(self.update, 1 / 60)

    # def update(self, dt):
    # pass

    def repopulate_sudoku(self):
        for button, number, original in zip(
            self.buttons,
            t.sudoku_array.flatten(),
            t.original_array.flatten(),
        ):
            button.text = str(number if number != 0 else "")
            button.is_locked = original != 0

    def highlight_placeable(self, number):
        for button, placeable in zip(self.buttons, t.get_placeable_cells(number)):
            button.is_highlighted = placeable

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

    def on_clear(self, instance):
        if self.selected_cell is not None:
            x, y = self.selected_cell.idx
            if t.original_array[x, y] == 0:
                t.sudoku_array[x, y] = 0
                self.buttons[x * 9 + y].text = ""
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

        self.selected_cell.text = str(self.selected_number.number)
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
    if platform == "win" or platform == "linux":
        Config.set("graphics", "resizable", False)
        # Window.size = (810, 540)
        # Window.size = (2468, 1118)

    # 2468 - 1000 = 1468
    # Poco 6 window size -> (2712, 1220)
    SudokuApp().run()
