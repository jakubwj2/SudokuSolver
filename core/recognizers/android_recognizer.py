from jnius import autoclass
import numpy as np

File = autoclass("java.io.File")
Interpreter = autoclass("org.tensorflow.lite.Interpreter")
InterpreterOptions = autoclass("org.tensorflow.lite.Interpreter$Options")
Tensor = autoclass("org.tensorflow.lite.Tensor")
DataType = autoclass("org.tensorflow.lite.DataType")
TensorBuffer = autoclass("org.tensorflow.lite.support.tensorbuffer.TensorBuffer")
ByteBuffer = autoclass("java.nio.ByteBuffer")


class AndroidRecognizer:
    def load(self, model_filename: str, num_threads: int | None = None) -> None:
        model = File(model_filename)
        options = InterpreterOptions()
        if num_threads is not None:
            options.setNumThreads(num_threads)
        self.interpreter = Interpreter(model, options)
        self._allocate_tensors()

    def _allocate_tensors(self):
        self.interpreter.allocateTensors()
        self.input_shape = self.interpreter.getInputTensor(0).shape()
        self.output_shape = self.interpreter.getOutputTensor(0).shape()
        self.output_type = self.interpreter.getOutputTensor(0).dataType()

    def get_input_shape(self):
        return self.input_shape

    def resize_input(self, shape: tuple[int, ...]) -> None:
        if self.input_shape != shape:
            self.interpreter.resizeInput(0, shape)
            self._allocate_tensors()

    def pred(self, x: np.ndarray) -> np.ndarray:
        x = np.array(x, dtype=np.float32)
        # assumes one input and one output for now
        input = ByteBuffer.wrap(x.tobytes())
        output = TensorBuffer.createFixedSize(self.output_shape, self.output_type)
        self.interpreter.run(input, output.getBuffer().rewind())
        return np.reshape(np.array(output.getFloatArray()), self.output_shape)
