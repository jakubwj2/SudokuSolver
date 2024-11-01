from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.gridlayout import GridLayout

from kivy.uix.button import Button
from sudoku import Table


class SudokuWidget(GridLayout):
    def __init__(self, sudoku: Table, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for i in range(9):
            self.add_widget(SudokuSection(sudoku.get_string_section_by_idx(i)))


class SudokuSection(GridLayout):
    def __init__(self, section, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for i in range(9):
            self.add_widget(SudokuButton(text=str(section[i])))


class SudokuButton(Button):
    id_counter = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = self.id_counter
        self.id_counter += 1


class DialButton(Button):
    pass


class DialWidget(GridLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for i in range(9):
            self.add_widget(DialButton(text=str(i + 1)))


class SideBarWidget(BoxLayout):
    pass


class MainLayout(BoxLayout):
    pass


class SudokuApp(App):
    def __init__(self, test_sudoku=None, **kwargs):
        super().__init__(**kwargs)
        self.table = Table() if test_sudoku is None else Table(test_sudoku)

    def build(self):
        main_layout = BoxLayout(
            orientation="horizontal",
            padding=(20, 20, 20, 20),
        )

        main_layout.add_widget(SudokuWidget(self.table))
        main_layout.add_widget(SideBarWidget())

        return main_layout


def enter_number(number):
    print("Number pressed:", number)


def press_solve():
    print("Solve pressed")


if __name__ == "__main__":
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
    SudokuApp(sudoku).run()
