import cv2
import numpy as np
import os

# import matplotlib.pyplot as plt
from model import TensorFlowModel


WIDTH = 450
HEIGHT = 450

path_to_model = "mnist_v03.tflite"
# model = tf.keras.models.load_model("mnist_v02.keras")
model = TensorFlowModel()
model.load(os.path.join(os.getcwd(), path_to_model))


def sudoku_pre_processing(img):
    img_gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
    img_blur = cv2.GaussianBlur(img_gray, (5, 5), 1)
    img_thresh = cv2.adaptiveThreshold(
        img_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    return img_thresh


def cell_pre_processing(img):
    crop = 7
    img = img[crop:-crop, crop:-crop]
    img = cv2.resize(img, (28, 28))
    # img = cv2.equalizeHist(img)
    img = img.reshape(img.shape[0], img.shape[1], 1)
    img = img / 255
    img = 1 - img
    return img


def largest_contour_area(contours):
    biggest = None
    max_area = 0
    for contour in contours:
        area = cv2.contourArea(contour)
        # We intend to increase the area by warping to a minimum of 63_504 (28^2*9^2) pixels
        # We are currently expanding the area to over 200_000 (for preprocessing purposes)
        if area < 10_000 or area < max_area:
            continue

        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) != 4:
            continue

        x, y, w, h = cv2.boundingRect(approx)
        aspect_ratio = float(w) / h
        if aspect_ratio < 0.9:
            continue

        bb_filled = area > (np.sqrt(w * w + h * h) / 2) ** 2
        if not bb_filled:
            continue

        biggest = approx
        max_area = area

    return biggest, max_area


def reorder_points(points):
    points = points.reshape((4, 2))
    new_points = np.zeros((4, 1, 2), dtype=np.int32)

    add = points.sum(1)
    new_points[0] = points[np.argmin(add)]
    new_points[3] = points[np.argmax(add)]

    diff = np.diff(points, axis=1)
    new_points[1] = points[np.argmin(diff)]
    new_points[2] = points[np.argmax(diff)]
    return new_points


def split_boxes(img):
    boxes = []
    for row in np.vsplit(img, 9):
        for box in np.hsplit(row, 9):
            boxes.append(box)
    return boxes


def draw_contours(
    frame: np.array,
    contours: tuple,
    indices: int = -1,
    thickness: int = 1,
    color: tuple = (0, 0, 255),
    alpha: float = 0.4,
):
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


def try_draw_sudoku_highlight(img):
    thresh = sudoku_pre_processing(img)
    contours, hierarchy = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    largest_contour, area = largest_contour_area(contours)
    if area == 0:
        return False, img

    draw_contours(img, [largest_contour], color=(255, 255, 0, 255), thickness=2)
    # cv2.drawContours(img, [largest_contour], -1, (255, 255, 0, 102), -1)
    # cv2.drawContours(img, [largest_contour], -1, (255, 255, 0, 255), 2)

    return True, img


def read_sudoku(img) -> np.ndarray | None:

    thresh = sudoku_pre_processing(img)
    contours, hierarchy = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    largest_contour, area = largest_contour_area(contours)

    if area == 0:
        print("No sudoku found!")
        return None

    largest_contour = reorder_points(largest_contour)

    pts1 = np.float32(largest_contour)
    pts2 = np.float32([[0, 0], [WIDTH, 0], [0, HEIGHT], [WIDTH, HEIGHT]])
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    imgWarpColored = cv2.warpPerspective(img, matrix, (WIDTH, HEIGHT))
    imgWarpGray = cv2.cvtColor(imgWarpColored, cv2.COLOR_BGR2GRAY)

    boxes = split_boxes(imgWarpGray)
    cells = np.array(list(map(cell_pre_processing, boxes)))

    predictions = []

    for cell in cells:
        predictions.append(model.pred([cell]))

    Y_pred_classes = np.argmax(predictions, axis=2)

    result = Y_pred_classes.reshape(9, 9)

    # print(result)

    # for pred, cell in zip(Y_pred_classes, cells):
    #     plt.imshow(cell, cmap="gray", vmin=0, vmax=1)
    #     plt.axis("off")
    #     plt.show()

    # plt.imshow(imgWarpGray, cmap="gray", vmin=0, vmax=255)
    # plt.axis("off")
    # plt.show()
    return result


if __name__ == "__main__":
    IMG_PATH = "sudoku_screenshots\\sudoku_7_4.png"

    array = read_sudoku(IMG_PATH)
    print(array)
