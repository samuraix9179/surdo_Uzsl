import builtins
import importlib
import os
import sys
import types
from unittest.mock import MagicMock, patch

# Add uzsl_bot to path so we can import from it
UZSL_BOT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "uzsl_bot"
)
if UZSL_BOT_PATH not in sys.path:
    sys.path.append(UZSL_BOT_PATH)


def _load_moderator_module():
    """Load utils.moderator with lightweight dependency stubs."""
    sys.modules.pop("utils.moderator", None)

    config_module = types.ModuleType("config")
    config_module.BOT_TOKEN = "test-token"

    database_module = types.ModuleType("database")

    async def _noop(*_args, **_kwargs):
        return None

    database_module.moderate_video = _noop
    database_module.get_video_owner = _noop

    telegram_module = types.ModuleType("telegram")
    telegram_module.Bot = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "config": config_module,
            "database": database_module,
            "telegram": telegram_module
        },
        clear=False
    ):
        return importlib.import_module("utils.moderator")


def _build_lazy_import_hook(mock_cv2, mock_mp, imported_modules):
    real_import = builtins.__import__

    def _import_with_mocks(name, globals=None, locals=None, fromlist=(), level=0):  # pylint: disable=redefined-builtin
        if name == "cv2":
            imported_modules.append(name)
            return mock_cv2
        if name == "mediapipe":
            imported_modules.append(name)
            return mock_mp
        return real_import(name, globals, locals, fromlist, level)

    return _import_with_mocks


def test_import_moderator_without_cv2_or_mediapipe():
    real_import = builtins.__import__

    def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # pylint: disable=redefined-builtin
        if name in {"cv2", "mediapipe"}:
            raise AssertionError(f"unexpected eager import: {name}")
        return real_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=_guarded_import):
        module = _load_moderator_module()

    assert callable(module.analyze_video_quality_sync)

@patch('os.path.exists', return_value=True)
def test_analyze_video_quality_sync_valid(_mock_exists):
    module = _load_moderator_module()
    mock_cv2 = MagicMock()
    mock_mp = MagicMock()
    mock_holistic_class = MagicMock()
    mock_mp.solutions.holistic.Holistic = mock_holistic_class
    imported_modules = []

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

    with patch(
        "builtins.__import__",
        side_effect=_build_lazy_import_hook(mock_cv2, mock_mp, imported_modules)
    ):
        analysis = module.analyze_video_quality_sync("dummy_path.mp4")

    assert analysis["ok"] is True
    assert analysis["face_ratio"] == 1.0
    assert analysis["left_hand_ratio"] == 1/3
    assert analysis["right_hand_ratio"] == 1/3
    assert imported_modules == ["cv2", "mediapipe"]


@patch('os.path.exists', return_value=True)
def test_analyze_video_quality_sync_invalid_face(_mock_exists):
    module = _load_moderator_module()
    mock_cv2 = MagicMock()
    mock_mp = MagicMock()
    mock_holistic_class = MagicMock()
    mock_mp.solutions.holistic.Holistic = mock_holistic_class
    imported_modules = []

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

    with patch(
        "builtins.__import__",
        side_effect=_build_lazy_import_hook(mock_cv2, mock_mp, imported_modules)
    ):
        analysis = module.analyze_video_quality_sync("dummy_path.mp4")

    assert analysis["ok"] is False
    assert analysis["rejection_reason"] == "incomplete"
    assert imported_modules == ["cv2", "mediapipe"]
