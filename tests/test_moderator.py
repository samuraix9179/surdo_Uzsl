import sys
import os
from unittest.mock import MagicMock, patch

# Inject mock modules in sys.modules BEFORE importing utils.moderator
mock_mp = MagicMock()
mock_holistic_class = MagicMock()
mock_mp.solutions.holistic.Holistic = mock_holistic_class
sys.modules['mediapipe'] = mock_mp

mock_cv2 = MagicMock()
sys.modules['cv2'] = mock_cv2

# Add uzsl_bot to path so we can import from it
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uzsl_bot"))

from utils.moderator import analyze_video_quality_sync  # noqa: E402


@patch('os.path.exists', return_value=True)
def test_analyze_video_quality_sync_valid(mock_exists):
    # Setup cv2.VideoCapture mock
    cap_inst = mock_cv2.VideoCapture.return_value
    cap_inst.isOpened.side_effect = [True, True, True, False]
    cap_inst.read.side_effect = [
        (True, "frame1"),
        (True, "frame2"),
        (True, "frame3"),
        (False, None)
    ]

    # Setup Holistic instance mock returning from context manager
    holistic_inst = mock_holistic_class.return_value.__enter__.return_value

    # Frame 1: Face + Left Hand
    res1 = MagicMock()
    res1.face_landmarks = "face"
    res1.left_hand_landmarks = "lh"
    res1.right_hand_landmarks = None

    # Frame 2: Face + Right Hand
    res2 = MagicMock()
    res2.face_landmarks = "face"
    res2.left_hand_landmarks = None
    res2.right_hand_landmarks = "rh"

    # Frame 3: Face only
    res3 = MagicMock()
    res3.face_landmarks = "face"
    res3.left_hand_landmarks = None
    res3.right_hand_landmarks = None

    holistic_inst.process.side_effect = [res1, res2, res3]

    analysis = analyze_video_quality_sync("dummy_path.mp4")

    assert analysis["ok"] is True
    assert analysis["face_ratio"] == 1.0
    assert analysis["left_hand_ratio"] == 1/3
    assert analysis["right_hand_ratio"] == 1/3


@patch('os.path.exists', return_value=True)
def test_analyze_video_quality_sync_invalid_face(mock_exists):
    # Setup cv2.VideoCapture mock
    cap_inst = mock_cv2.VideoCapture.return_value
    cap_inst.isOpened.side_effect = [True, True, False]
    cap_inst.read.side_effect = [
        (True, "frame1"),
        (True, "frame2"),
        (False, None)
    ]

    # Setup Holistic instance mock returning from context manager
    holistic_inst = mock_holistic_class.return_value.__enter__.return_value

    # Frame 1: No Face + Left Hand
    res1 = MagicMock()
    res1.face_landmarks = None
    res1.left_hand_landmarks = "lh"
    res1.right_hand_landmarks = None

    # Frame 2: Face + Right Hand
    res2 = MagicMock()
    res2.face_landmarks = "face"
    res2.left_hand_landmarks = None
    res2.right_hand_landmarks = "rh"

    holistic_inst.process.side_effect = [res1, res2]

    analysis = analyze_video_quality_sync("dummy_path.mp4")

    assert analysis["ok"] is False
    assert analysis["rejection_reason"] == "incomplete"
