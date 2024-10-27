from collections.abc import Iterator
from itertools import product
import numpy as np
from time import time


class table:
    def __init__(self, array=None, empty=" "):
        self.sudoku_array = np.array(array) if array is not None else np.zeros((9, 9))
        self.empty = empty
        self.notes = np.ndarray((9, 9), dtype=list)
        self.original_array = np.array(self.sudoku_array)

    def is_empty(self, row_idx: int, column_idx: int) -> bool:
        return self.sudoku_array[row_idx, column_idx] == 0

    def place(
        self, value: int, row_idx: int, column_idx: int, force: bool = False
    ) -> None:
        if self.is_empty(row_idx, column_idx) or force:
            self.sudoku_array[row_idx, column_idx] = value
        else:
            raise ValueError(
                "Cannot place value in a filled cell", value, row_idx, column_idx
            )

    # def fill_subsection(
    #     self,
    #     value: int,
    #     subsection_row_idx: int,
    #     subsection_column_idx: int,
    #     force: bool = False,
    # ) -> None:
    #     for i in range(3):
    #         for j in range(3):
    #             self.place(
    #                 value,
    #                 subsection_row_idx * 3 + i,
    #                 subsection_column_idx * 3 + j,
    #                 force,
    #             )

    # def fill_row(self, value: int, row_idx: int, force: bool = False) -> None:
    #     for i in range(9):
    #         self.place(value, row_idx, i, force)

    # def fill_column(self, value: int, column_idx: int, force: bool = False) -> None:
    #     for i in range(9):
    #         self.place(value, i, column_idx, force)

    def check_section(self, value: int, x: int, y: int) -> bool:
        return bool(np.all(self.get_section(self.sudoku_array, x, y) != value))

    def get_section_by_idx(self, array: np.ndarray, idx: int) -> np.ndarray:
        return self.get_section(array, idx // 3, idx % 3)

    def get_section(self, array: np.ndarray, x: int, y: int) -> np.ndarray:
        return array[x * 3 : (x + 1) * 3, y * 3 : (y + 1) * 3]

    def check_row(self, value: int, row_idx: int) -> bool:
        return bool(np.all(self.sudoku_array[row_idx, :] != value))

    def check_column(self, value: int, column_idx: int) -> bool:
        return bool(np.all(self.sudoku_array[:, column_idx] != value))

    def check_placeable(self, value: int, row_idx: int, column_idx: int) -> bool:
        return (
            self.is_empty(row_idx, column_idx)
            and self.check_row(value, row_idx)
            and self.check_column(value, column_idx)
            and self.check_section(value, row_idx // 3, column_idx // 3)
        )

    def placeable_coords_generator(self, value: int) -> Iterator[tuple]:
        for x, y in product(range(9), range(9)):
            if self.check_placeable(value, x, y):
                yield (x, y)

    def write_all_notes(self) -> None:
        self.notes.fill(None)
        for number, x, y in product(range(1, 10), range(9), range(9)):
            if self.check_placeable(number, x, y):
                if self.notes[x, y] is None:
                    self.notes[x, y] = [number]
                else:
                    self.notes[x, y].append(number)

    def filter_notes(self):
        self.write_all_notes()

        # section_shapes = np.zeros()
        # too many numbers wanna be in a cell
        # if the same number of notes for multiple numbers is the same as the number of  in a section
        # there must be a number in a row/column
        # if all notes in a sections are in a row/column,
        # then the number can't appear in other sections in the same row/column
        pass

    def cell_has_1_note(self, number, array):
        return sum([number in notes for notes in array if notes]) == 1

    def find_new_values(self) -> None:
        row_sums = np.zeros((9, 9))
        column_sums = np.zeros((9, 9))
        section_sums = np.zeros((3, 3, 9))

        for number, idx in product(range(9), range(9)):
            row_sums[idx, number] = self.cell_has_1_note(number + 1, self.notes[idx])

            column_sums[idx, number] = self.cell_has_1_note(
                number + 1, self.notes[:, idx]
            )

            sub_section = self.get_section_by_idx(self.notes, idx).flatten()
            section_sums[idx // 3, idx % 3, number] = self.cell_has_1_note(
                number + 1, sub_section
            )

        for x, y in product(range(9), range(9)):
            if self.notes[x, y] is None:
                continue

            if len(self.notes[x, y]) == 1:
                self.sudoku_array[x, y] = self.notes[x, y][0]
                continue

            for array in [row_sums[x], column_sums[y], section_sums[x // 3, y // 3]]:
                for number in array.nonzero()[0] + 1:
                    if self.notes_contain(number, x, y):
                        self.sudoku_array[x, y] = number
                        break

    def solve(self) -> None:
        prev_num_filled_cells = -1
        while self.num_filled_cells(self.sudoku_array) > prev_num_filled_cells:
            prev_num_filled_cells = self.num_filled_cells(self.sudoku_array)
            self.filter_notes()
            self.find_new_values()

    def validate(self) -> bool:
        for idx in range(9):
            if len(set(self.sudoku_array[idx]) - {0}) != np.count_nonzero(
                self.sudoku_array[idx]
            ):
                print("Not all values are unique in row %s" % idx)
                return False
            if len(set(self.sudoku_array[:, idx]) - {0}) != np.count_nonzero(
                self.sudoku_array[:, idx]
            ):
                print("Not all values are unique in column %s" % idx)
                return False

        for section_row_idx in range(3):
            for section_column_idx in range(3):
                sub_section = self.sudoku_array[
                    section_row_idx * 3 : (section_row_idx + 1) * 3,
                    section_column_idx * 3 : (section_column_idx + 1) * 3,
                ]

                if len(set(sub_section.flatten()) - {0}) != np.count_nonzero(
                    sub_section
                ):
                    print(
                        "Not all numbers in section {}x{} have unique values".format(
                            section_row_idx, section_column_idx
                        )
                    )
                    return False
        return True

    def num_filled_cells(self, array) -> int:
        return np.count_nonzero(array)

    def notes_contain(self, value, x, y) -> bool:
        return self.notes[x, y] and value in self.notes[x, y]

    def print(self) -> None:
        for row in self.__print_table_row(self.sudoku_array, self.empty):
            print(row)

    def print_notes(self) -> None:
        for row in self.__print_table_row(self.notes, self.empty):
            print(row)

    def compare_print(self) -> None:
        print("Original Sudoku" + "\t" * 3 + "Solved Sudoku")
        for original_array_row, array_row in zip(
            t.__print_table_row(t.original_array, " "),
            t.__print_table_row(t.sudoku_array, " "),
        ):
            print(original_array_row, "\t", end="")
            print(array_row)
        print(
            "Filled Cells: \n"
            + str(self.num_filled_cells(self.original_array))
            + "\t" * 4
            + str(self.num_filled_cells(self.sudoku_array)),
        )

    def __print_table_row(self, array, empty) -> Iterator[str]:
        for x in range(9):
            result = ""
            if x % 3 == 0:
                yield "-" * 25
            for y in range(9):
                if y % 3 == 0:
                    result += "| "
                result += (
                    empty
                    if isinstance(array[x, y], np.int64) and array[x, y] == 0
                    else str(array[x, y])
                )
                result += " "
            result += "|"
            yield result
        yield "-" * 25


if __name__ == "__main__":
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
        [0, 1, 0, 7, 0, 0, 9, 3, 0],
        [6, 9, 0, 0, 0, 2, 0, 1, 7],
        [0, 0, 0, 0, 0, 6, 8, 2, 4],
        [2, 6, 0, 0, 7, 8, 0, 4, 0],
        [5, 8, 1, 4, 0, 9, 0, 7, 0],
        [0, 7, 0, 5, 6, 1, 0, 0, 8],
        [0, 3, 5, 0, 0, 0, 7, 0, 2],
        [7, 0, 0, 6, 1, 0, 0, 0, 9],
        [0, 0, 0, 0, 0, 7, 0, 0, 0],
    ]

    start = time()
    t = table(sudoku, empty=" ")

    # for value in range(1, 10):
    #     for cords in t.placeable_coords_generator(value):
    #         t.place(value, cords[0], cords[1])

    # t.print()
    # t.print_notes()
    # t.print()

    t.solve()
    t.compare_print()

    print("Solution", "Valid" if t.validate() else "Invalid")
    print("Completed in:", time() - start)
