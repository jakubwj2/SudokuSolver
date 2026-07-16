from collections.abc import Iterator
from itertools import islice, product
from time import time

import numpy as np


class Table:
    """Sudoku table class."""

    def __init__(self, array=None, empty=" "):
        """Initialize the Sudoku table.

        Args:
            array (list, optional): The Sudoku array. Defaults to None.
            empty (str, optional): The empty value. Defaults to " ".
        """
        self.sudoku_array = (
            np.array(array) if array is not None else np.zeros((9, 9), dtype=np.int8)
        )
        self.empty = empty
        self.candidates = np.ndarray((9, 9), dtype=list)
        self.original_array = np.array(self.sudoku_array)
        self.gen_candidates()
        self.solutions = list()

    def is_empty(self, row_idx: int, column_idx: int) -> np.bool:
        """Check if the cell is empty.
        Args:
            row_idx (int): The row index.
            column_idx (int): The column index.
        Returns:
            np.bool: True if the cell is empty, False otherwise.
        """
        return self.sudoku_array[row_idx, column_idx] == 0

    def get_section_by_idx(self, array: np.ndarray, idx: int) -> np.ndarray:
        """Get the section by index.
        Args:
            array (np.ndarray): The array to get the section from.
            idx (int): The flattened section index.
        Returns:
            np.ndarray: The section.
        """
        return self.get_section(array, idx // 3, idx % 3)

    def get_section(self, array: np.ndarray, x: int, y: int) -> np.ndarray:
        """Get the section by x and y.
        Args:
            array (np.ndarray): The array to get the section from.
            x (int): The x index of the section.
            y (int): The y index of the section.
        Returns:
            np.ndarray: The section.
        """
        return array[x * 3 : (x + 1) * 3, y * 3 : (y + 1) * 3]

    def is_valid_row_for_number(
        self, number: int, row_idx: int, column_idx: int
    ) -> np.bool:
        """Check if the cell with the given row and column index is valid for the number.
        Args:
            number (int): The number to check.
            row_idx (int): The row index of the cell.
            column_idx (int): The column index of the cell.
        Returns:
            np.bool: True if the cell is valid for the number, False otherwise.
        """
        return np.all(self.sudoku_array[row_idx, :column_idx] != number) and np.all(
            self.sudoku_array[row_idx, column_idx + 1 :] != number
        )

    def is_valid_column_for_number(
        self, number: int, row_idx: int, column_idx: int
    ) -> np.bool:
        """Check if the cell with the given row and column index is valid for the number.
        Args:
            number (int): The number to check.
            row_idx (int): The row index of the cell.
            column_idx (int): The column index of the cell.
        Returns:
            np.bool: True if the cell is valid for the number, False otherwise.
        """
        return np.all(self.sudoku_array[:row_idx, column_idx] != number) and np.all(
            self.sudoku_array[row_idx + 1 :, column_idx] != number
        )

    def is_valid_section_for_number(
        self, number: int, row_idx: int, column_idx: int
    ) -> np.bool:
        """Check if the cell with the given row and column index is valid for the number.
        Args:
            number (int): The number to check.
            row_idx (int): The row index of the cell.
            column_idx (int): The column index of the cell.
        Returns:
            np.bool: True if the cell is valid for the number, False otherwise.
        """
        section = self.get_section(self.sudoku_array, row_idx // 3, column_idx // 3)
        section_array = section.flatten()

        idx = row_idx % 3 * 3 + column_idx % 3
        return np.all(section_array[:idx] != number) and np.all(
            section_array[idx + 1 :] != number
        )

    def get_valid_cells_for_number(self, number: int | None) -> list:
        """Get the valid cells for a number.
        Args:
            number (int | None): The number to get the valid cells for.
        Returns:
            list: The valid cells for the number.
        """
        if number is None:
            return list(np.full(81, False))
        result = []
        for x, y in product(range(9), range(9)):
            result.append(self.candidates_contain(number, x, y))
        return result

    def is_valid_cell_for_number(
        self, number: int, row_idx: int, column_idx: int
    ) -> np.bool:
        """Check if the cell with the given row and column index is valid for the number.
        Args:
            number (int): The number to check.
            row_idx (int): The row index of the cell.
            column_idx (int): The column index of the cell.
        Returns:
            np.bool: True if the cell is valid for the number, False otherwise.
        """
        return (
            self.is_valid_row_for_number(number, row_idx, column_idx)
            and self.is_valid_column_for_number(number, row_idx, column_idx)
            and self.is_valid_section_for_number(number, row_idx, column_idx)
        )

    def gen_candidates(self) -> None:
        """Generate the candidates for all cells in the table."""
        self.candidates.fill(None)
        for number, x, y in product(range(1, 10), range(9), range(9)):
            if self.is_empty(x, y) and self.is_valid_cell_for_number(number, x, y):
                if self.candidates[x, y] is None:
                    self.candidates[x, y] = [number]
                else:
                    self.candidates[x, y].append(number)

    # def filter_candidates(self):
    #     for number in range(1, 10):
    #         number_in_candidates = np.zeros((9, 9), dtype=np.int64)
    #         in_row = np.zeros((9, 3))
    #         in_column = np.zeros((9, 3))

    #         for x, y in product(range(9), range(9)):
    #             number_in_candidates[x, y] = self.candidates_contain(number, x, y)

    #         for idx in range(9):
    #             section = self.get_section_by_idx(number_in_candidates, idx)
    #             in_row[idx] = np.any(section, axis=1)
    #             in_column[idx] = np.any(section, axis=0)

    #         for x, y in product(range(3), range(3)):
    #             if sum(in_row[x * 3 + y]) == 1:
    #                 replace_x = in_row[x * 3 + y].nonzero()[0]
    #                 for i in range(3):
    #                     if i != y:
    #                         section = self.get_section(self.candidates, x, i)
    #                         self.remove_candidate_from_cells(number, section[replace_x])

    #             if sum(in_column[x * 3 + y]) == 1:
    #                 replace_y = in_column[x * 3 + y].nonzero()[0]
    #                 for i in range(3):
    #                     if i != x:
    #                         section = self.get_section(self.candidates, i, y)
    #                         self.remove_candidate_from_cells(
    #                             number, section[:, replace_y]
    #                         )

    # for i in range(3):
    #     col1 = i
    #     col2 = 3 + i
    #     col3 = 6 + i

    #     self.xwing(number, col1, col2, col3, in_column, True)
    #     self.xwing(number, col2, col3, col1, in_column, True)
    #     self.xwing(number, col1, col3, col2, in_column, True)

    #     row1 = i * 3
    #     row2 = i * 3 + 1
    #     row3 = i * 3 + 2

    #     self.xwing(number, row1, row2, row3, in_row, False)
    #     self.xwing(number, row2, row3, row1, in_row, False)
    #     self.xwing(number, row1, row3, row2, in_row, False)

    # def xwing(self, number, check_idx1, check_idx2, change_idx3, in_line, is_column):
    #     if sum(in_line[check_idx1]) == 2 and all(
    #         in_line[check_idx1] == in_line[check_idx2]
    #     ):
    #         subsection = self.get_section_by_idx(self.candidates, change_idx3)
    #         for subsection_column in range(3):
    #             if in_line[check_idx1][subsection_column]:
    #                 if is_column:
    #                     self.remove_candidate_from_cells(
    #                         number, subsection[:, subsection_column]
    #                     )
    #                 else:
    #                     self.remove_candidate_from_cells(
    #                         number, subsection[subsection_column]
    #                     )

    def remove_candidate_from_cells(self, number: int, cells: np.ndarray) -> None:
        """Remove a candidate from each cell in the cells array.
        Args:
            number (int): The number to remove.
            cells (np.ndarray): The cells to remove the candidate from.
        """
        for cell in cells.flatten():
            if cell and number in cell:
                cell.remove(number)

    # def single_candidate_in_list(self, number: int, array: np.ndarray) -> bool:
    #     """Check if the number is the only candidate in the array.
    #     Args:
    #         number (int): The number to check.
    #         array (np.ndarray): The array to check.
    #     Returns:
    #         bool: True if the number is the only candidate in the array, False otherwise.
    #     """
    #     return sum([number in candidates for candidates in array if candidates]) == 1

    # def find_new_values(self) -> None:
    #     row_sums = np.zeros((9, 9))
    #     column_sums = np.zeros((9, 9))
    #     section_sums = np.zeros((3, 3, 9))

    #     for number, idx in product(range(9), range(9)):
    #         row_sums[idx, number] = self.single_candidate_in_list(
    #             number + 1, self.candidates[idx]
    #         )

    #         column_sums[idx, number] = self.single_candidate_in_list(
    #             number + 1, self.candidates[:, idx]
    #         )

    #         sub_section = self.get_section_by_idx(self.candidates, idx).flatten()
    #         section_sums[idx // 3, idx % 3, number] = self.single_candidate_in_list(
    #             number + 1, sub_section
    #         )

    #     for x, y in product(range(9), range(9)):
    #         if self.candidates[x, y] is None:
    #             continue

    #         if len(self.candidates[x, y]) == 1:
    #             self.insert_number(self.candidates[x, y][0], x, y)
    #             continue

    #         for array in [row_sums[x], column_sums[y], section_sums[x // 3, y // 3]]:
    #             for number in array.nonzero()[0] + 1:
    #                 if self.candidates_contain(number, x, y):
    #                     self.insert_number(number, x, y)
    #                     break

    def insert_number(self, number: int, x: int, y: int) -> None:
        """Insert a number into the cell with the given row and column index. Remove the number from the candidates of the row, column and section.
        Args:
            number (int): The number to insert.
            x (int): The row index of the cell.
            y (int): The column index of the cell.
        """
        self.sudoku_array[x, y] = number
        self.candidates[x, y] = None

        self.remove_candidate_from_cells(number, self.candidates[:, y])
        self.remove_candidate_from_cells(number, self.candidates[x])
        self.remove_candidate_from_cells(
            number, self.get_section(self.candidates, x // 3, y // 3)
        )

    def solve(self, single_solution: bool = True) -> None:
        """Solve the Sudoku puzzle using backpropagation.
        Args:
            single_solution (bool, optional): Whether to solve for a single solution or all solutions. Defaults to True.
        """
        # prev_num_candidates = float("inf")
        # self.gen_candidates()

        # while (
        #     self.num_candidates() < prev_num_candidates
        #     and self.num_filled_cells(self.sudoku_array) < 81
        # ):
        #     prev_num_candidates = self.num_candidates()
        #     self.find_new_values()
        #     if self.num_candidates() == prev_num_candidates:
        #         self.filter_candidates()

        if np.count_nonzero(self.sudoku_array) < 81:
            self.solutions = []
            if single_solution:
                self._backpropagation_single_solutonion(0)
            else:
                self._backpropagation_all_solutions(0)
            if len(self.solutions) != 0:
                self.sudoku_array = self.solutions[0]

    def _backpropagation_single_solutonion(self, start_idx) -> bool:
        """Solve the Sudoku puzzle using backpropagation for a single solution."""
        for x, y in islice(product(range(9), range(9)), start_idx, 81):
            if not self.is_empty(x, y):
                continue

            for n in self.get_valid_numbers_for_cell(x, y):
                self.sudoku_array[x, y] = n
                if self._backpropagation_single_solutonion(x * 9 + y + 1):
                    return True
                self.sudoku_array[x, y] = 0
            return False

        self.solutions.append(self.sudoku_array.copy())
        return True

    def _backpropagation_all_solutions(self, start_idx):
        """Solve the Sudoku puzzle using backpropagation for all solutions."""
        for x, y in islice(product(range(9), range(9)), start_idx, 81):
            if not self.is_empty(x, y):
                continue

            for n in self.get_valid_numbers_for_cell(x, y):
                self.sudoku_array[x, y] = n
                self._backpropagation_all_solutions(x * 9 + y + 1)
                self.sudoku_array[x, y] = 0
            return

        self.solutions.append(self.sudoku_array.copy())
        print(len(self.solutions), end="\r")

    def get_valid_numbers_for_cell(self, x: int, y: int) -> list:
        """Get the valid numbers for the cell with the given row and column index.
        Args:
            x (int): The row index of the cell.
            y (int): The column index of the cell.
        Returns:
            list: The valid numbers for the cell.
        """

        row = set(cell for idx, cell in enumerate(self.sudoku_array[x]) if idx != y)

        column = set(
            cell for idx, cell in enumerate(self.sudoku_array[:, y]) if idx != x
        )

        section_array = self.get_section(self.sudoku_array, x // 3, y // 3).flatten()
        cell_idx = x % 3 * 3 + y % 3
        section = set(cell for idx, cell in enumerate(section_array) if idx != cell_idx)

        return list(set(range(1, 10)) - row - column - section)

    def test_all_solutions(self):
        for solution_idx in range(len(self.solutions)):
            solution = self.solutions[solution_idx]
            assert self.validate(solution)
            assert np.count_nonzero(solution) == 81
            for other_solution_idx in range(solution_idx + 1, len(self.solutions)):
                assert not np.all(solution == self.solutions[other_solution_idx])

    def validate(self, array) -> bool:
        result = True
        for idx in range(9):
            if len(set(array[idx]) - {0}) != np.count_nonzero(array[idx]):
                print("Not all values are unique in row %s" % idx)
                result = False

            if len(set(array[:, idx]) - {0}) != np.count_nonzero(array[:, idx]):
                print("Not all values are unique in column %s" % idx)
                result = False

            section = self.get_section_by_idx(array, idx)
            if len(set(section.flatten()) - {0}) != np.count_nonzero(section):
                print("Not all values are unique in section %s" % idx)
                result = False

        return result

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
            self.__print_table_row(self.original_array, " "),
            self.__print_table_row(self.sudoku_array, " "),
        ):
            print(original_array_row, "\t", end="")
            print(array_row)
        print(
            "Filled Cells: \n"
            + str(np.count_nonzero(self.original_array))
            + "\t" * 4
            + str(np.count_nonzero(self.sudoku_array)),
        )

    def __print_table_row(self, array, empty) -> Iterator[str]:
        for x in range(9):
            result = ""
            if x % 3 == 0:
                yield "-" * 25
            for y in range(9):
                if y % 3 == 0:
                    result += "| "
                result += empty if array[x, y] == 0 else str(array[x, y])
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

    def replace_sudoku(self, new_sudoku: np.ndarray | None) -> None:
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
    for _ in range(10):
        t = Table(sudoku, empty=" ")
        t.solve(single_solution=False)
    end = time() - start

    t.test_all_solutions()

    t.compare_print()

    print("Solution", "Valid" if t.validate(t.sudoku_array) else "Invalid")
    print("Number of solutions:", len(t.solutions))
    print("Completed in:", end)

    # print("Number of left over candidates:", t.num_candidates())
