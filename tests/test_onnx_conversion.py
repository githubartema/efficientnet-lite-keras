import os
import shutil
import subprocess
import tempfile
from typing import Tuple

import onnxruntime
import tensorflow as tf
from absl.testing import absltest, parameterized

from tests.test_efficientnet_lite import TEST_PARAMS

# Disable GPU
tf.config.set_visible_devices([], "GPU")


class TestONNXConversion(parameterized.TestCase):
    rng = tf.random.Generator.from_non_deterministic_state()
    saved_model_path = os.path.join(tempfile.mkdtemp(), "saved_model")
    onnx_model_path = os.path.join(tempfile.mkdtemp(), "model.onnx")

    def tearDown(self) -> None:
        if os.path.exists(self.onnx_model_path):
            os.remove(self.onnx_model_path)
        if os.path.exists(self.saved_model_path):
            shutil.rmtree(self.saved_model_path)

    @parameterized.named_parameters(TEST_PARAMS)
    def test_model_onnx_conversion(
        self, model: tf.keras.Model, input_shape: Tuple[int, int]
    ):
        model = model(weights=None)
        model.save(self.saved_model_path)

        self._convert_onnx()
        self.assertTrue(os.path.isfile(self.onnx_model_path))

        # Compare outputs:
        mock_input = self.rng.uniform(shape=(1, *input_shape, 3), dtype=tf.float32)
        original_output = model.predict(mock_input)

        onnx_session = onnxruntime.InferenceSession(self.onnx_model_path)
        onnx_inputs = {onnx_session.get_inputs()[0].name: mock_input.numpy()}
        onnx_output = onnx_session.run(None, onnx_inputs)

        tf.debugging.assert_near(original_output, onnx_output, rtol=1e-3, atol=1e-3)

    def _convert_onnx(self):
        command = (
            f"python -m tf2onnx.convert "
            f"--saved-model {self.saved_model_path} "
            f"--output {self.onnx_model_path} "
        )
        subprocess.run(command, shell=True, check=True)


if __name__ == "__main__":
    absltest.main()