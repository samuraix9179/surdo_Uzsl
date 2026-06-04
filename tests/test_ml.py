import sys
import os
import pytest

# Add root and uzsl_bot directories to sys.path for test imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uzsl_bot"))

try:
    import torch
except ImportError:
    torch = None

from ml_training.predict_pipeline import UZSLPipeline  # noqa: E402
from ml_training.utils.yolo_predictor import YOLOSignPredictor  # noqa: E402


def test_continuous_slr_shape():
    """Verify the ContinuousSLR network output shapes."""
    if torch is None:
        pytest.skip("PyTorch is not installed")

    from ml_training.models.continuous_slr import ContinuousSLR

    batch_size = 2
    in_channels = 3
    num_frames = 30
    num_nodes = 543
    num_classes = 10

    model = ContinuousSLR(
        in_channels=in_channels,
        num_classes=num_classes,
        num_nodes=num_nodes,
        hidden_dim=64,
        num_layers=1
    )

    # Input shape: (batch_size, in_channels, num_frames, num_nodes)
    inputs = torch.randn(batch_size, in_channels, num_frames, num_nodes)
    outputs = model(inputs)

    # Output shape: (batch_size, num_frames, num_classes + 1)
    assert outputs.shape == (batch_size, num_frames, num_classes + 1)


def test_uzsl_pipeline():
    """Verify that UZSLPipeline maps predictions to natural Uzbek sentences."""
    pipeline = UZSLPipeline()
    dummy_sequence = [{"pose": [0.0] * 99, "left_hand": [0.0] * 63, "right_hand": [0.0] * 63}] * 30

    output_sentence = pipeline.process_landmarks(dummy_sequence)

    # The default mock returns ['men', 'do'kon', 'bormoq'] which conjugates to:
    assert output_sentence == "Men do'konga boryapman."


def test_yolo_predictor():
    """Verify that YOLOSignPredictor returns class and confidence."""
    predictor = YOLOSignPredictor()
    pred = predictor.predict_dactyl("dummy_image.jpg")

    assert "class" in pred
    assert "confidence" in pred
    assert pred["confidence"] >= 0.0
