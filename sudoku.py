from collections.abc import Iterator
from itertools import product
import numpy as np
from time import time


class Table:
    def __init__(self, array=None, empty=" "):
        self.sudoku_array = (
            np.array(array) if array is not None else np.zeros((9, 9), dtype=np.int8)
        )
        self.empty = empty
        self.candidates = np.ndarray((9, 9), dtype=list)
        self.original_array = np.array(self.sudoku_array)
        self.gen_candidates()

    def is_empty(self, row_idx: int, column_idx: int) -> bool:
        return self.sudoku_array[row_idx, column_idx] == 0

    def place(
        self, value: int, row_idx: int, column_idx: int, force: bool = False
    ) -> bool:
        if self.original_array[row_idx, column_idx] == 0 or force:
            self.insert_number(value, row_idx, column_idx)
            return True
        return False

    def get_section_by_idx(self, array: np.ndarray, idx: int) -> np.ndarray:
        return self.get_section(array, idx // 3, idx % 3)

    def get_section(self, array: np.ndarray, x: int, y: int) -> np.ndarray:
        return array[x * 3 : (x + 1) * 3, y * 3 : (y + 1) * 3]

    def check_placeable(self, number: int, row_idx: int, column_idx: int) -> bool:
        return (
            self.is_empty(row_idx, column_idx)
            and np.all(self.sudoku_array[row_idx, :] != number)
            and np.all(self.sudoku_array[:, column_idx] != number)
            and np.all(
                self.get_section(self.sudoku_array, row_idx // 3, column_idx // 3)
                != number
            )
        )

    def get_placeable_cells(self, number: int) -> list:
        if number is None:
            # return [False for _ in range(81)]
            return list(np.full(81, False))
        result = []
        for x, y in product(range(9), range(9)):
            result.append(self.candidates_contain(number, x, y))
        return result

    def gen_candidates(self) -> None:
        self.candidates.fill(None)
        for number, x, y in product(range(1, 10), range(9), range(9)):
            if self.check_placeable(number, x, y):
                if self.candidates[x, y] is None:
                    self.candidates[x, y] = [number]
                else:
                    self.candidates[x, y].append(number)

    def filter_candidates(self):
        for number in range(1, 10):
            number_in_candidates = np.zeros((9, 9), dtype=np.int64)
            in_row = np.zeros((9, 3))
            in_column = np.zeros((9, 3))

            for x, y in product(range(9), range(9)):
                number_in_candidates[x, y] = self.candidates_contain(number, x, y)

            for idx in range(9):
                section = self.get_section_by_idx(number_in_candidates, idx)
                in_row[idx] = np.any(section, axis=1)
                in_column[idx] = np.any(section, axis=0)

            for x, y in product(range(3), range(3)):
                if sum(in_row[x * 3 + y]) == 1:
                    replace_x = in_row[x * 3 + y].nonzero()[0]
                    for i in range(3):
                        if i != y:
                            section = self.get_section(self.candidates, x, i)
                            self.remove_candidate_from_cells(number, section[replace_x])

                if sum(in_column[x * 3 + y]) == 1:
                    replace_y = in_column[x * 3 + y].nonzero()[0]
                    for i in range(3):
                        if i != x:
                            section = self.get_section(self.candidates, i, y)
                            self.remove_candidate_from_cells(
                                number, section[:, replace_y]
                            )

            for i in range(3):
                col1 = i
                col2 = 3 + i
                col3 = 6 + i

                self.xwing(number, col1, col2, col3, in_column, True)
                self.xwing(number, col2, col3, col1, in_column, True)
                self.xwing(number, col1, col3, col2, in_column, True)

                row1 = i * 3
                row2 = i * 3 + 1
                row3 = i * 3 + 2

                self.xwing(number, row1, row2, row3, in_row, False)
                self.xwing(number, row2, row3, row1, in_row, False)
                self.xwing(number, row1, row3, row2, in_row, False)

    def xwing(self, number, check_idx1, check_idx2, change_idx3, in_line, is_column):
        if sum(in_line[check_idx1]) == 2 and all(
            in_line[check_idx1] == in_line[check_idx2]
        ):
            subsection = self.get_section_by_idx(self.candidates, change_idx3)
            for subsection_column in range(3):
                if in_line[check_idx1][subsection_column]:
                    if is_column:
                        self.remove_candidate_from_cells(
                            number, subsection[:, subsection_column]
                        )
                    else:
                        self.remove_candidate_from_cells(
                            number, subsection[subsection_column]
                        )

    def remove_candidate_from_cells(self, number: int, cells: np.ndarray) -> None:
        for cell in cells.flatten():
            if cell and number in cell:
                cell.remove(number)

    def single_candidate_in_list(self, number: int, array: np.ndarray) -> bool:
        return sum([number in candidates for candidates in array if candidates]) == 1

    def find_new_values(self) -> None:
        row_sums = np.zeros((9, 9))
        column_sums = np.zeros((9, 9))
        section_sums = np.zeros((3, 3, 9))

        for number, idx in product(range(9), range(9)):
            row_sums[idx, number] = self.single_candidate_in_list(
                number + 1, self.candidates[idx]
            )

            column_sums[idx, number] = self.single_candidate_in_list(
                number + 1, self.candidates[:, idx]
            )

            sub_section = self.get_section_by_idx(self.candidates, idx).flatten()
            section_sums[idx // 3, idx % 3, number] = self.single_candidate_in_list(
                number + 1, sub_section
            )

        for x, y in product(range(9), range(9)):
            if self.candidates[x, y] is None:
                continue

            if len(self.candidates[x, y]) == 1:
                self.insert_number(self.candidates[x, y][0], x, y)
                continue

            for array in [row_sums[x], column_sums[y], section_sums[x // 3, y // 3]]:
                for number in array.nonzero()[0] + 1:
                    if self.candidates_contain(number, x, y):
                        self.insert_number(number, x, y)
                        break

    def insert_number(self, number: int, x: int, y: int) -> None:
        self.sudoku_array[x, y] = number
        self.candidates[x, y] = None

        self.remove_candidate_from_cells(number, self.candidates[:, y])
        self.remove_candidate_from_cells(number, self.candidates[x])
        self.remove_candidate_from_cells(
            number, self.get_section(self.candidates, x // 3, y // 3)
        )

    def solve(self) -> None:
        prev_num_candidates = float("inf")
        self.gen_candidates()

        while (
            self.num_candidates() < prev_num_candidates
            and self.num_filled_cells(self.sudoku_array) < 81
        ):
            prev_num_candidates = self.num_candidates()
            self.find_new_values()
            if self.num_candidates() == prev_num_candidates:
                self.filter_candidates()

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

    def num_candidates(self) -> int:
        result = 0
        for cell_candidates in self.candidates.flatten():
            if cell_candidates is not None:
                result += len(cell_candidates)
        return result

    def candidates_contain(self, number: int, x: int, y: int) -> bool:
        return self.candidates[x, y] is not None and number in self.candidates[x, y]

    def print(self) -> None:
        for row in self.__print_table_row(self.sudoku_array, self.empty):
            print(row)

    def print_candidates(self) -> None:
        for row in self.__print_table_row(self.candidates, self.empty):
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

    def get_string_section_by_idx(self, idx: int) -> list:
        current_section = self.get_section_by_idx(self.sudoku_array, idx).flatten()
        return [str(x if x != 0 else self.empty) for x in current_section]

    def reset(self):
        self.sudoku_array = self.original_array.copy()
        self.gen_candidates()

    def replace_sudoku(self, new_sudoku: np.ndarray) -> None:
        if new_sudoku is None:
            self.__init__()
            return

        assert new_sudoku.shape == (9, 9)
        self.sudoku_array = new_sudoku
        self.gen_candidates()


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

    start = time()
    t.solve()
    end = time() - start

    t.compare_print()

    print("Solution", "Valid" if t.validate() else "Invalid")
    print("Completed in:", end)

    print("Number of left over candidates:", t.num_candidates())
