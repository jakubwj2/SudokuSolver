from __future__ import annotations

import cv2
import numpy as np

from core.config import get_config
from core.recognizers import get_digit_recognizer
from core.recognizers.protocol import DigitRecognizer
from core.vision import reorder_points

_model: DigitRecognizer | None = None


def _get_model() -> DigitRecognizer:
    global _model
    if _model is None:
        _model = get_digit_recognizer()
        _model.load(str(get_config().paths.model))
    return _model


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
    img = 1.0 - img
    return img


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


def read_sudoku(img: np.ndarray, contour: np.ndarray) -> np.ndarray:
    """
    Read the sudoku digits from ``img`` using a known grid contour.

    Args:
        img (np.ndarray): The sudoku image to read.
        contour (np.ndarray): The contour of the sudoku to read.

    Returns:
        np.ndarray: The sudoku array.
    """
    contour = reorder_points(contour)

    width = 450
    height = 450

    pts1 = np.array(contour, dtype=np.float32)
    pts2 = np.array(
        [[0, 0], [width, 0], [0, height], [width, height]], dtype=np.float32
    )
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    imgWarpColored = cv2.warpPerspective(img, matrix, (width, height))
    imgWarpGray = cv2.cvtColor(imgWarpColored, cv2.COLOR_RGBA2GRAY)

    boxes = split_boxes(imgWarpGray)
    cells = np.array(list(map(cell_pre_processing, boxes)))

    predictions = []

    model = _get_model()
    for cell in cells:
        predictions.append(model.pred(np.array([cell])))

    Y_pred_classes = np.argmax(predictions, axis=2)

    result = Y_pred_classes.reshape(9, 9)

    return result
