from typing import Protocol
import numpy as np


class DigitRecognizer(Protocol):
    def load(self, model_filename: str, num_threads: int | None = None) -> None: ...
    def pred(self, x: np.ndarray) -> np.ndarray: ...
