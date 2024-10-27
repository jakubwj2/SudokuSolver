import numpy as np
from sudoku import table


def test_check_section_empty_subsection():
    t = table()
    for x in range(3):
        for y in range(3):
            assert t.check_section(1, x, y) is True


def test_check_section_value_in_top_left_corner():
    for x in range(3):
        for y in range(3):
            t = table()
            t.place(1, x, y)
            assert t.check_section(1, 0, 0) is False


def test_check_section_all_identical_except_target():
    for i in range(9):
        t = table()
        # Fill subsection (0,0) with the value 2
        t.fill_subsection(i, 0, 0)
        # Place the target value 1 in one cell of the subsection (0,0)
        t.place(1, 0, 0)
        # Check if the subsection (0,0) contains the value 1
        assert t.check_section(1, 0, 0) is False


def test_check_section_multiple_instances_of_target_value():
    t = table()
    # Fill subsection (0,0) with the value 1
    t.fill_subsection(1, 0, 0)
    # Place another instance of the value 1 in the same subsection
    t.place(2, 1, 1)
    # Check if the subsection (0,0) contains the value 1
    assert t.check_section(2, 0, 0) is False
