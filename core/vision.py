from __future__ import annotations

from typing import Sequence

import cv2
import numpy as np

from core.config import get_config
from core.recognizers import get_digit_recognizer
from core.recognizers.protocol import DigitRecognizer

_model: DigitRecognizer | None = None

# Contour detection runs on a downscaled copy; corners are mapped back to full-res.
_DETECT_MAX_WIDTH = 480
# Minimum contour area at "full" scale (~252x252). Scaled down with the detect image.
_MIN_CONTOUR_AREA = 63_504
# Blur / adaptive-threshold sizes were tuned for full-HD camera frames; scale with width.
_PREPROCESS_REF_WIDTH = 1920

# Geometric priors for quad candidates (relative to the detection-frame size).
_MIN_AREA_FRAME_FRAC = 0.15
_MAX_AREA_FRAME_FRAC = 0.85
_MIN_ASPECT = 0.85
_MAX_ASPECT = 1.15
_MIN_BORDER_MARGIN_PX = 2
_BORDER_MARGIN_FRAC = 0.02


def _get_model() -> DigitRecognizer:
    global _model
    if _model is None:
        _model = get_digit_recognizer()
        _model.load(str(get_config().paths.model))
    return _model


def _odd_kernel(size: float, *, minimum: int = 3) -> int:
    """Round to an odd kernel size >= ``minimum`` (OpenCV requirement)."""
    size = max(minimum, int(round(size)))
    if size % 2 == 0:
        size += 1
    return size


def _prepare_detection_image(img: np.ndarray) -> tuple[np.ndarray, float]:
    """Return a detection-sized image and the factor to map coords back to ``img``."""
    height, width = img.shape[:2]
    if width <= _DETECT_MAX_WIDTH:
        return img, 1.0

    scale = width / _DETECT_MAX_WIDTH
    small = cv2.resize(
        img,
        (_DETECT_MAX_WIDTH, int(round(height / scale))),
        interpolation=cv2.INTER_AREA,
    )
    return small, scale


def sudoku_pre_processing(img: np.ndarray) -> np.ndarray:
    """
    Preprocess an RGBA frame for contour detection.

    Blur and adaptive-threshold block size scale with image width so downscaled
    detection stays comparable to the original 1920-wide tuning. Callers (e.g.
    ``KivyCamera``) are expected to convert to RGBA before this runs.

    Args:
        img (np.ndarray): The sudoku image to preprocess.

    Returns:
        np.ndarray: The preprocessed sudoku image.
    """
    width = img.shape[1]
    scale = width / _PREPROCESS_REF_WIDTH
    blur_k = _odd_kernel(5 * scale)
    block_size = _odd_kernel(11 * scale)

    img_gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
    img_blur = cv2.GaussianBlur(img_gray, (blur_k, blur_k), 0)
    img_thresh = cv2.adaptiveThreshold(
        img_blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        block_size,
        2,
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
    img = 1.0 - img
    return img


def _border_hug_count(
    quad: np.ndarray,
    frame_width: int,
    frame_height: int,
    margin: int,
) -> int:
    """How many corners lie within ``margin`` px of the frame edge."""
    count = 0
    for x, y in quad.reshape(-1, 2):
        if (
            x <= margin
            or y <= margin
            or x >= frame_width - 1 - margin
            or y >= frame_height - 1 - margin
        ):
            count += 1
    return count


def largest_contour_area(
    contours: Sequence[np.ndarray],
    *,
    frame_shape: tuple[int, int],
    min_area: float = _MIN_CONTOUR_AREA,
) -> np.ndarray | None:
    """
    Pick the best sudoku-like 4-point contour.

    Applies geometric priors (area fraction, near-square aspect, convexity),
    prefers quads whose corners are inset from the frame border, then largest area.
    """
    frame_height, frame_width = frame_shape[:2]
    frame_area = float(frame_width * frame_height)
    area_lo = max(min_area, _MIN_AREA_FRAME_FRAC * frame_area)
    area_hi = _MAX_AREA_FRAME_FRAC * frame_area
    margin = max(
        _MIN_BORDER_MARGIN_PX,
        int(round(_BORDER_MARGIN_FRAC * min(frame_width, frame_height))),
    )

    # (border_hug_count, -area, quad) — lower hug first, then larger area
    best_key: tuple[int, float] | None = None
    best_quad: np.ndarray | None = None

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < area_lo or area > area_hi:
            continue

        perimeter = cv2.arcLength(contour, True)
        quad = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(quad) != 4 or not cv2.isContourConvex(quad):
            continue

        _center, (rect_w, rect_h), _angle = cv2.minAreaRect(quad)
        if rect_w < 1.0 or rect_h < 1.0:
            continue
        aspect = rect_w / rect_h
        if aspect < _MIN_ASPECT or aspect > _MAX_ASPECT:
            continue

        hug = _border_hug_count(quad, frame_width, frame_height, margin)
        key = (hug, -area)
        if best_key is None or key < best_key:
            best_key = key
            best_quad = quad

    return best_quad


def find_sudoku_quad(img: np.ndarray) -> np.ndarray | None:
    """
    Find the best sudoku-like quad in ``img``.

    Pipeline: downscale → preprocess → contours → candidate filter → best pick.
    Returns a 4-point contour in full-resolution image coordinates, or ``None``.
    """
    small, scale = _prepare_detection_image(img)
    thresh = sudoku_pre_processing(small)
    contours, _hierarchy = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    min_area = _MIN_CONTOUR_AREA / (scale**2)
    largest_contour = largest_contour_area(
        contours,
        frame_shape=small.shape[:2],
        min_area=min_area,
    )
    if largest_contour is None:
        return None

    if scale != 1.0:
        largest_contour = np.round(largest_contour.astype(np.float64) * scale).astype(
            np.int32
        )
    return largest_contour


def reorder_points(points: np.ndarray) -> np.ndarray:
    """
    Order quad corners for perspective warp.

    Returns points in the order top-left, top-right, bottom-left, bottom-right
    (matching ``pts2`` used with ``cv2.getPerspectiveTransform``).
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
    largest_contour = find_sudoku_quad(img)
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
    largest_contour = find_sudoku_quad(img)

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


if __name__ == "__main__":
    import time

    start_time = time.time()
    IMG_PATH = "SudokuPhotos/2026-07-14_17-21-01.png"
    img = np.array(cv2.imread(IMG_PATH))
    array = read_sudoku(img)
    print(array)
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")
