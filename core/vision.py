from __future__ import annotations

import bisect
from dataclasses import dataclass
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

# Multi-candidate grid scoring (on the detection-sized frame).
_TOP_QUAD_CANDIDATES = 5
_GRID_WARP_SIZE = 225
_MIN_GRID_SCORE = 0.3
_GRID_PEAK_THRESH = 0.25
_IDEAL_GRID_LINES = 10
_GRID_LINE_SPAN_FRAC = 0.45


@dataclass(frozen=True, slots=True)
class QuadCandidate:
    """A geometry-valid quad before grid scoring."""

    area: float
    quad: np.ndarray


@dataclass(frozen=True, slots=True)
class GridScore:
    """How grid-like a warped quad looks."""

    value: float
    horizontal_lines: int
    vertical_lines: int


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


def sudoku_pre_processing(img: np.ndarray, scale: float) -> np.ndarray:
    """
    Preprocess an RGBA frame for contour detection.

    Blur and adaptive-threshold block size scale with image width so downscaled
    detection stays comparable to the original 1920-wide tuning. Callers (e.g.
    ``KivyCamera``) are expected to convert to RGBA before this runs.

    Args:
        img (np.ndarray): The sudoku image to preprocess.
        scale (float): The scale factor to map coords back to ``img``.
    Returns:
        np.ndarray: The preprocessed sudoku image.
    """
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


def _geometry_quad_candidates(
    contours: Sequence[np.ndarray],
    *,
    frame_shape: tuple[int, int],
    min_area: float = _MIN_CONTOUR_AREA,
    top_n: int = _TOP_QUAD_CANDIDATES,
) -> list[QuadCandidate]:
    """
    Return up to ``top_n`` geometry-valid quads, largest area first.

    Priors: area fraction, near-square ``minAreaRect`` aspect, convexity.
    """
    frame_height, frame_width = frame_shape[:2]
    frame_area = float(frame_width * frame_height)
    area_lo = max(min_area, _MIN_AREA_FRAME_FRAC * frame_area)
    area_hi = _MAX_AREA_FRAME_FRAC * frame_area

    scored: list[QuadCandidate] = []
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

        if len(scored) < top_n:
            bisect.insort(
                scored, QuadCandidate(area=area, quad=quad), key=lambda item: item.area
            )
        elif area > scored[0].area:
            bisect.insort(scored, scored[0], key=lambda item: item.area)
            scored.pop(0)

    return scored


def _count_projection_peaks(proj: np.ndarray) -> int:
    """Count local maxima in a 1-D projection (heuristic for grid lines)."""
    if proj.size < 3 or float(proj.max()) <= 0:
        return 0

    p = proj.astype(np.float64) / float(proj.max())
    # Light smooth only — heavy blur merges neighboring grid lines.
    p = cv2.GaussianBlur(p.reshape(-1, 1), (1, 3), 0).ravel()

    peaks = 0
    for i in range(1, len(p) - 1):
        if p[i] >= _GRID_PEAK_THRESH and p[i] >= p[i - 1] and p[i] > p[i + 1]:
            peaks += 1
    return peaks


def _count_long_line_components(line_mask: np.ndarray, *, horizontal: bool) -> int:
    """Count connected components that span most of the warp (grid lines)."""
    _nlabels, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
        line_mask, connectivity=8
    )
    if horizontal:
        min_span = _GRID_LINE_SPAN_FRAC * line_mask.shape[1]
        return sum(
            1 for i in range(1, _nlabels) if stats[i, cv2.CC_STAT_WIDTH] >= min_span
        )
    min_span = _GRID_LINE_SPAN_FRAC * line_mask.shape[0]
    return sum(
        1 for i in range(1, _nlabels) if stats[i, cv2.CC_STAT_HEIGHT] >= min_span
    )


def _line_count_score(line_count: int) -> float:
    """Reward ~8-10 lines (sudoku has 10 grid lines including borders)."""
    if line_count < 5:
        return 0.0
    return max(0.0, 1.0 - abs(line_count - _IDEAL_GRID_LINES) / 8.0)


def _score_sudoku_grid(gray_square: np.ndarray) -> GridScore:
    """
    Score how grid-like a warped square looks.

    Uses morphological horizontal/vertical line extraction plus projection peaks
    and long connected components. ``GridScore.value`` is in ``[0, 1]``.
    """
    # # gray_square needs to be set to blur when using the GaussianBlur
    # blur = cv2.GaussianBlur(gray_square, (3, 3), 0)
    thr = cv2.adaptiveThreshold(
        gray_square,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11,
        2,
    )
    n = gray_square.shape[0]
    klen = max(n // 20, 9)
    if klen % 2 == 0:
        klen += 1

    horizontal = cv2.morphologyEx(
        thr,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (klen, 1)),
    )
    vertical = cv2.morphologyEx(
        thr,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, klen)),
    )

    h_lines = max(
        _count_projection_peaks(np.sum(horizontal, axis=1)),
        _count_long_line_components(horizontal, horizontal=True),
    )
    v_lines = max(
        _count_projection_peaks(np.sum(vertical, axis=0)),
        _count_long_line_components(vertical, horizontal=False),
    )
    value = 0.5 * (_line_count_score(h_lines) + _line_count_score(v_lines))
    return GridScore(
        value=value,
        horizontal_lines=h_lines,
        vertical_lines=v_lines,
    )


def _warp_quad_gray(
    gray: np.ndarray,
    quad: np.ndarray,
    size: int = _GRID_WARP_SIZE,
) -> np.ndarray:
    ordered = reorder_points(quad).astype(np.float32)
    pts1 = ordered.reshape(4, 2)
    pts2 = np.array(
        [[0, 0], [size, 0], [0, size], [size, size]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    return cv2.warpPerspective(gray, matrix, (size, size))


def find_sudoku_quad(img: np.ndarray) -> np.ndarray | None:
    """
    Find the best sudoku-like quad in ``img``.

    Pipeline: downscale → preprocess → contours → geometry filter → top-N candidates →
    grid-score warped crops → best above threshold.

    Returns a 4-point contour in full-resolution image coordinates, or ``None``.
    """
    small, scale = _prepare_detection_image(img)
    thresh = sudoku_pre_processing(small, 1.0 / scale)
    contours, _hierarchy = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    min_area = _MIN_CONTOUR_AREA / (scale**2)
    candidates = _geometry_quad_candidates(
        contours,
        frame_shape=small.shape[:2],
        min_area=min_area,
    )
    if not candidates:
        return None

    gray = cv2.cvtColor(small, cv2.COLOR_RGBA2GRAY)
    best_quad: np.ndarray | None = None
    best_score = -1.0
    for candidate in candidates:
        warped = _warp_quad_gray(gray, candidate.quad)
        score = _score_sudoku_grid(warped)
        if score.value > best_score:
            best_score = score.value
            best_quad = candidate.quad

    if best_quad is None or best_score < _MIN_GRID_SCORE:
        return None

    if scale != 1.0:
        best_quad = np.round(best_quad.astype(np.float64) * scale).astype(np.int32)
    return best_quad


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


def read_sudoku(img: np.ndarray, contour: np.ndarray) -> np.ndarray:
    """
    Read the sudoku from the image.

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


if __name__ == "__main__":
    import time

    start_time = time.time()
    IMG_PATH = "SudokuPhotos/2026-07-14_17-21-01.png"
    img = np.array(cv2.imread(IMG_PATH))
    contour = find_sudoku_quad(img)
    if contour is None:
        print("No sudoku found!")
        raise ValueError("No sudoku found!")

    array = read_sudoku(img, contour)
    print(array)
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")
