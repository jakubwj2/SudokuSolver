from typing import Sequence

import cv2
import numpy as np

from app_config import get_config
from recognizers import get_digit_recognizer

model = get_digit_recognizer()
model.load(str(get_config().paths.model))


def sudoku_pre_processing(img: np.ndarray) -> np.ndarray:
    """
    Preprocess the image to make Computer Vision more accurate and consistent.

    Args:
        img (np.ndarray): The sudoku image to preprocess.

    Returns:
        np.ndarray: The preprocessed sudoku image.
    """
    img_gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
    img_blur = cv2.GaussianBlur(img_gray, (5, 5), 1)
    img_thresh = cv2.adaptiveThreshold(
        img_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    return img_thresh


def cell_pre_processing(img: np.ndarray) -> np.ndarray:
    """
    Preprocess the individual cells to make Machine Learning more accurate and consistent.

    Args:
        img (np.ndarray): The individual cell image to preprocess.

    Returns:
        np.ndarray: The preprocessed individual cell image.
    """
    crop = 7
    img = img[crop:-crop, crop:-crop]
    img = cv2.resize(img, (28, 28))
    # img = cv2.equalizeHist(img)
    img = img.reshape(img.shape[0], img.shape[1], 1)
    img = img / 255
    img = 1 - img
    return img


def largest_contour_area(contours: Sequence[np.ndarray]) -> np.ndarray | None:
    """
    Find the largest contour from a list of contours.

    Args:
        contours (Sequence[np.ndarray]): A list of contours to find the largest from.

    Returns:
        tuple[np.ndarray | None, float]: The largest contour and its area.
    """

    largest_contour: np.ndarray | None = None
    max_area: float = 0
    for contour in contours:
        area = cv2.contourArea(contour)
        # We intend to increase the area by warping to a minimum of 63_504 (28^2*9^2) pixels
        # We are currently expanding the area to over 200_000 (for preprocessing purposes)
        if area < 63_504 or area < max_area:
            continue

        perimeter = cv2.arcLength(contour, True)
        simplified_contour = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(simplified_contour) != 4:
            continue

        x, y, w, h = cv2.boundingRect(simplified_contour)
        aspect_ratio = float(w) / h
        if aspect_ratio < 0.9:
            continue

        bb_filled = area > (np.sqrt(w * w + h * h) / 2) ** 2
        if not bb_filled:
            continue

        largest_contour = simplified_contour
        max_area = area

    return largest_contour


def reorder_points(points: np.ndarray) -> np.ndarray:
    """
    # Order the points of a countour by their widht and then by their height.

    Args:
        points (np.ndarray): The points to reorder.

    Returns:
        np.ndarray: The reordered points in the order of top-left, top-right, bottom-right, bottom-left.
    """
    points = points.reshape((4, 2))
    new_points = np.zeros((4, 1, 2), dtype=np.int32)

    add = points.sum(1)
    new_points[0] = points[np.argmin(add)]
    new_points[3] = points[np.argmax(add)]

    diff = np.diff(points, axis=1)
    new_points[1] = points[np.argmin(diff)]
    new_points[2] = points[np.argmax(diff)]
    return new_points


def split_boxes(img: np.ndarray) -> list[np.ndarray]:
    """
    Split the sudoku into 81 individual cells.

    Args:
        img (np.ndarray): The sudoku image to split.

    Returns:
        list[np.ndarray]: A flattened list of individual cells.
    """
    boxes = []
    for row in np.vsplit(img, 9):
        for box in np.hsplit(row, 9):
            boxes.append(box)
    return boxes


def draw_contours(
    frame: np.ndarray,
    contours: Sequence[np.ndarray],
    indices: int = -1,
    thickness: int = 1,
    color: tuple = (0, 0, 255),
    alpha: float = 0.4,
) -> None:
    """
    Draw in-place some contours in a frame.

    Args:
        frame (np.array): The input frame.
        contours (tuple): The contours defining the mask.
        indices (int): The index of the contours to be drawn.
            Pass ``-1`` to consider all of them.
        color (tuple): The color used to draw the contours.
        alpha (float): A value between ``0.0`` (transparent)
            and ``1.0`` (opaque).
        thickness (int): The thickness of the contours.
    """
    if alpha:
        mask = np.zeros(frame.shape, np.uint8)
        cv2.drawContours(mask, contours, indices, color, -1)
        frame[:] = cv2.addWeighted(mask, alpha, frame, beta=1.0, gamma=0.0)
    cv2.drawContours(frame, contours, indices, color, thickness)


def try_draw_sudoku_highlight(img: np.ndarray) -> tuple[bool, np.ndarray]:
    """
    Try to draw a highlight around the sudoku.

    Args:
        img (np.ndarray): The sudoku image to draw the highlight on.

    Returns:
        tuple[bool, np.ndarray]: A tuple containing a boolean indicating success and the image with the highlight.
    """
    thresh = sudoku_pre_processing(img)
    contours, hierarchy = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    largest_contour = largest_contour_area(contours)
    if largest_contour is None:
        return False, img

    draw_contours(img, [largest_contour], color=(255, 255, 0, 255), thickness=2)
    return True, img


def read_sudoku(img: np.ndarray) -> np.ndarray | None:
    """
    Read the sudoku from the image.

    Args:
        img (np.ndarray): The sudoku image to read.

    Returns:
        np.ndarray | None: The sudoku array or None if no sudoku is found.
    """
    thresh = sudoku_pre_processing(img)
    contours, hierarchy = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    largest_contour = largest_contour_area(contours)

    if largest_contour is None:
        print("No sudoku found!")
        return None

    largest_contour = reorder_points(largest_contour)

    width = 450
    height = 450

    pts1 = np.array(largest_contour, dtype=np.float32)
    pts2 = np.array(
        [[0, 0], [width, 0], [0, height], [width, height]], dtype=np.float32
    )
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    imgWarpColored = cv2.warpPerspective(img, matrix, (width, height))
    imgWarpGray = cv2.cvtColor(imgWarpColored, cv2.COLOR_BGR2GRAY)

    boxes = split_boxes(imgWarpGray)
    cells = np.array(list(map(cell_pre_processing, boxes)))

    predictions = []

    for cell in cells:
        predictions.append(model.pred(np.array([cell])))

    Y_pred_classes = np.argmax(predictions, axis=2)

    result = Y_pred_classes.reshape(9, 9)

    return result


if __name__ == "__main__":
    IMG_PATH = "SudokuPhotos/2026-07-14_17-21-01.png"
    img = np.array(cv2.imread(IMG_PATH))
    array = read_sudoku(img)
    print(array)
