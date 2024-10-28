from collections.abc import Iterator
from itertools import product
import numpy as np
from time import time


class Table:
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
        for number in range(1, 10):
            number_in_notes = np.zeros((9, 9), dtype=np.int64)
            rows = np.zeros((9, 3))
            columns = np.zeros((9, 3))

            for x, y in product(range(9), range(9)):
                number_in_notes[x, y] = self.notes_contain(number, x, y)

            for idx in range(9):
                section = self.get_section_by_idx(number_in_notes, idx)
                rows[idx] = np.any(section, axis=1)
                columns[idx] = np.any(section, axis=0)

            for x, y in product(range(3), range(3)):
                if sum(rows[x * 3 + y]) == 1:
                    replace_x = rows[x * 3 + y].nonzero()[0]
                    for section in [
                        self.get_section(self.notes, x, i) for i in range(3) if i != y
                    ]:
                        for i in range(3):
                            cell_notes = section[replace_x, i][0]
                            if cell_notes is not None and number in cell_notes:
                                cell_notes.remove(number)

                if sum(columns[x * 3 + y]) == 1:
                    replace_y = columns[x * 3 + y].nonzero()[0]
                    for section in [
                        self.get_section(self.notes, i, y) for i in range(3) if i != x
                    ]:
                        for i in range(3):
                            cell_notes = section[i, replace_y][0]
                            if cell_notes is not None and number in cell_notes:
                                cell_notes.remove(number)

            for x in range(3):
                row1 = rows[x * 3]
                row2 = rows[x * 3 + 1]
                row3 = rows[x * 3 + 2]
                if sum(row1) + sum(row2) == 4 and all(row1 == row2):
                    subsection = self.get_section_by_idx(self.notes, x * 3 + 2)
                    for subsection_row in range(3):
                        if row1[subsection_row]:
                            for cell in subsection[subsection_row, :]:
                                if cell and number in cell:
                                    cell.remove(number)

                if sum(row2) + sum(row3) == 4 and all(row2 == row3):
                    subsection = self.get_section_by_idx(self.notes, x * 3)
                    for subsection_row in range(3):
                        if row2[subsection_row]:
                            for cell in subsection[subsection_row, :]:
                                if cell and number in cell:
                                    cell.remove(number)

                if sum(row1) + sum(row3) == 4 and all(row1 == row3):
                    subsection = self.get_section_by_idx(self.notes, x * 3 + 1)
                    for subsection_row in range(3):
                        if row1[subsection_row]:
                            for cell in subsection[subsection_row, :]:
                                if cell and number in cell:
                                    cell.remove(number)

            for y in range(3):
                column1 = columns[y]
                column2 = columns[3 + y]
                column3 = columns[6 + y]

                if sum(column1) + sum(column2) == 4 and all(column1 == column2):
                    subsection = self.get_section_by_idx(self.notes, 6 + y)
                    for subsection_column in range(3):
                        if column1[subsection_column]:
                            for cell in subsection[:, subsection_column]:
                                if cell and number in cell:
                                    cell.remove(number)

                if sum(column2) + sum(column3) == 4 and all(column2 == column3):
                    subsection = self.get_section_by_idx(self.notes, y)
                    for subsection_column in range(3):
                        if column2[subsection_column]:
                            for cell in subsection[:, subsection_column]:
                                if cell and number in cell:
                                    cell.remove(number)

                if sum(column1) + sum(column3) == 4 and all(column1 == column3):
                    subsection = self.get_section_by_idx(self.notes, 3 + y)
                    for subsection_column in range(3):
                        if column1[subsection_column]:
                            for cell in subsection[:, subsection_column]:
                                if cell and number in cell:
                                    cell.remove(number)

            print()
            print(number)
            for row in self.__print_table_row(number_in_notes, " "):
                print(row)

    def note_in_1_place(self, number, array):
        return sum([number in notes for notes in array if notes]) == 1

    def find_new_values(self) -> None:
        row_sums = np.zeros((9, 9))
        column_sums = np.zeros((9, 9))
        section_sums = np.zeros((3, 3, 9))

        for number, idx in product(range(9), range(9)):
            row_sums[idx, number] = self.note_in_1_place(number + 1, self.notes[idx])

            column_sums[idx, number] = self.note_in_1_place(
                number + 1, self.notes[:, idx]
            )

            sub_section = self.get_section_by_idx(self.notes, idx).flatten()
            section_sums[idx // 3, idx % 3, number] = self.note_in_1_place(
                number + 1, sub_section
            )

        for x, y in product(range(9), range(9)):
            if self.notes[x, y] is None:
                continue

            if len(self.notes[x, y]) == 1:
                self.insert_number(self.notes[x, y][0], x, y)
                continue

            for array in [row_sums[x], column_sums[y], section_sums[x // 3, y // 3]]:
                for number in array.nonzero()[0] + 1:
                    if self.notes_contain(number, x, y):
                        self.insert_number(number, x, y)
                        break

    def insert_number(self, number: int, x: int, y: int) -> None:
        self.sudoku_array[x, y] = number
        self.notes[x, y] = None

        for idx in range(9):
            row_notes = self.notes[idx, y]
            if row_notes and number in row_notes:
                row_notes.remove(number)

            column_notes = self.notes[x, idx]
            if column_notes and number in column_notes:
                column_notes.remove(number)

        for x_idx, y_idx in product(
            range(x - x % 3, x - x % 3 + 3), range(y - y % 3, y - y % 3 + 3)
        ):
            section_notes = self.notes[x_idx, y_idx]
            if section_notes and number in section_notes:
                section_notes.remove(number)

    def solve(self) -> None:
        prev_num_notes = float("inf")
        self.write_all_notes()

        while self.num_notes() < prev_num_notes:
            prev_num_notes = self.num_notes()
            self.find_new_values()
            if self.num_notes() < prev_num_notes:
                self.filter_notes()

    def validate(self) -> bool:
        result = True
        for idx in range(9):
            if len(set(self.sudoku_array[idx]) - {0}) != np.count_nonzero(
                self.sudoku_array[idx]
            ):
                print("Not all values are unique in row %s" % idx)
                result = False
            if len(set(self.sudoku_array[:, idx]) - {0}) != np.count_nonzero(
                self.sudoku_array[:, idx]
            ):
                print("Not all values are unique in column %s" % idx)
                result = False

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
                    result = False
        return result

    def num_filled_cells(self, array) -> int:
        return np.count_nonzero(array)

    def num_notes(self) -> int:
        result = 0
        for cell_notes in self.notes.flatten():
            if cell_notes is not None:
                result += len(cell_notes)
        return result

    def notes_contain(self, number: int, x: int, y: int) -> bool:
        return self.notes[x, y] is not None and number in self.notes[x, y]

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

    # sudoku = [
    #     [0, 1, 0, 7, 0, 0, 9, 3, 0],
    #     [6, 9, 0, 0, 0, 2, 0, 1, 7],
    #     [0, 0, 0, 0, 0, 6, 8, 2, 4],
    #     [2, 6, 0, 0, 7, 8, 0, 4, 0],
    #     [5, 8, 1, 4, 0, 9, 0, 7, 0],
    #     [0, 7, 0, 5, 6, 1, 0, 0, 8],
    #     [0, 3, 5, 0, 0, 0, 7, 0, 2],
    #     [7, 0, 0, 6, 1, 0, 0, 0, 9],
    #     [0, 0, 0, 0, 0, 7, 0, 0, 0],
    # ]

    t = Table(sudoku, empty=" ")

    # for value in range(1, 10):
    #     for cords in t.placeable_coords_generator(value):
    #         t.place(value, cords[0], cords[1])

    # t.print()
    # t.print_notes()
    # t.print()

    start = time()
    t.solve()
    end = time() - start
    t.compare_print()

    print("Solution", "Valid" if t.validate() else "Invalid")
    print("Completed in:", end)

    print(t.num_notes())
