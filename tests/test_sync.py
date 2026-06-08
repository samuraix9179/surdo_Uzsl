import os
import sys
import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Inject mock modules in sys.modules BEFORE importing anything that imports cv2/mediapipe
mock_mp = MagicMock()
mock_holistic_class = MagicMock()
mock_mp.solutions.holistic.Holistic = mock_holistic_class
sys.modules['mediapipe'] = mock_mp

mock_cv2 = MagicMock()
sys.modules['cv2'] = mock_cv2

# Mock huggingface_hub
mock_hf = MagicMock()
sys.modules['huggingface_hub'] = mock_hf

# Add uzsl_bot to path so we can import from it
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uzsl_bot"))

import config  # noqa: E402
config.DB_PATH = "test_sync.db"
config.SUPABASE_DB_URL = None  # Force SQLite for testing
config.HF_TOKEN = "test_token"
config.HUGGINGFACE_REPO = "test/repo"
config.BOT_TOKEN = "123456:testtoken"

from database import init_db, create_user, save_video, get_all_labels, get_video_by_id  # noqa: E402
from utils.sync_to_huggingface import sync_video_to_huggingface  # noqa: E402


@pytest.mark.asyncio
async def test_sync_video_to_huggingface():
    """sync_video_to_huggingface funksiyasi videoni yuklab olib, landmarks ajratib S3 ga yuklashini tekshiradi."""
    if os.path.exists("test_sync.db"):
        os.remove("test_sync.db")

    # Mock Telegram Bot
    mock_bot_class = MagicMock()
    mock_bot_instance = AsyncMock()
    mock_bot_class.return_value = mock_bot_instance

    mock_file = AsyncMock()
    mock_file.download_to_drive = AsyncMock()
    mock_bot_instance.get_file.return_value = mock_file

    # Mock extract_landmarks.process_video
    mock_sequence = [{"pose": [0.1, 0.2, 0.3], "face": [], "left_hand": [], "right_hand": []}]

    # Mock upload_file_to_s3
    mock_upload = AsyncMock(side_effect=lambda local_path, s3_key: f"https://s3.example.com/{s3_key}")

    # Mock HF Api
    mock_api_instance = MagicMock()
    mock_hf.HfApi.return_value = mock_api_instance
    mock_api_instance.upload_file = MagicMock()

    try:
        await init_db()
        labels = await get_all_labels()
        label_id = labels[0]["label_id"]

        # Create user & video
        user_id = 12345
        await create_user(user_id, "volunteer", "Volunteer Name")
        video_id = await save_video(
            user_id=user_id,
            label_id=label_id,
            file_id="telegram_file_id_xyz",
            duration=2.5,
            file_size=300000,
            width=640,
            height=480
        )

        with patch('utils.sync_to_huggingface.Bot', mock_bot_class), \
             patch('utils.sync_to_huggingface.process_video', return_value=mock_sequence), \
             patch('utils.sync_to_huggingface.upload_file_to_s3', mock_upload):

            # Run sync
            success = await sync_video_to_huggingface(video_id)
            assert success is True

            # Verify video details updated in DB
            video = await get_video_by_id(video_id)
            assert video["s3_url"] is not None
            assert "videos/" in video["s3_url"]
            assert video["landmarks_url"] is not None
            assert "landmarks/" in video["landmarks_url"]

            # Check files were created locally under exports directory
            expected_video_path = os.path.join(
                config.EXPORT_DIR, "videos", video["category"],
                f"{video['word_uz']}_{video_id}_{user_id}.mp4"
            )
            expected_landmarks_path = os.path.join(
                config.EXPORT_DIR, "landmarks", video["category"],
                f"{video['word_uz']}_{video_id}_{user_id}.json"
            )

            # Since we mocked the download and processing, let's verify if sync_video_to_huggingface wrote json
            assert os.path.exists(expected_landmarks_path)
            with open(expected_landmarks_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                assert data["frames_count"] == 1
                assert data["metadata"]["video_id"] == video_id

            # Verify glossary and dataset_info files were created
            expected_glossary_path = os.path.join(config.EXPORT_DIR, "glossary.json")
            expected_info_path = os.path.join(config.EXPORT_DIR, "dataset_info.json")

            assert os.path.exists(expected_glossary_path)
            assert os.path.exists(expected_info_path)

            with open(expected_glossary_path, "r", encoding="utf-8") as f:
                glossary = json.load(f)
                assert len(glossary) > 0
                matched_label = next((item for item in glossary if item["word_uz"] == video["word_uz"]), None)
                assert matched_label is not None
                assert matched_label["word_uz"] == video["word_uz"]

            with open(expected_info_path, "r", encoding="utf-8") as f:
                info = json.load(f)
                assert info["total_words"] > 0

            # Clean up local exports files
            if os.path.exists(expected_landmarks_path):
                os.remove(expected_landmarks_path)
            if os.path.exists(expected_video_path):
                os.remove(expected_video_path)
            if os.path.exists(expected_glossary_path):
                os.remove(expected_glossary_path)
            if os.path.exists(expected_info_path):
                os.remove(expected_info_path)

    finally:
        if os.path.exists("test_sync.db"):
            os.remove("test_sync.db")
