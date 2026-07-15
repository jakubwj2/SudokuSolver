from ai_edge_litert.interpreter import Interpreter as LiteRtInterpreter
import numpy as np
from typing import Any


class DesktopRecognizer:
    def load(self, model_filename: str, num_threads: int | None = None) -> None:
        kwargs: dict[str, Any] = {"model_path": model_filename}
        if num_threads is not None:
            kwargs["num_threads"] = num_threads
        self.interpreter = LiteRtInterpreter(**kwargs)
        self.interpreter.allocate_tensors()

    def resize_input(self, shape: tuple[int, ...]) -> None:
        if list(self.get_input_shape()) != shape:
            self.interpreter.resize_tensor_input(0, shape)
            self.interpreter.allocate_tensors()

    def get_input_shape(self) -> tuple[int, ...]:
        return self.interpreter.get_input_details()[0]["shape"]

    def pred(self, x: np.ndarray) -> np.ndarray:
        x = np.array(x, dtype=np.float32)
        # assumes one input and one output for now
        self.interpreter.set_tensor(self.interpreter.get_input_details()[0]["index"], x)
        self.interpreter.invoke()
        return self.interpreter.get_tensor(
            self.interpreter.get_output_details()[0]["index"]
        )
