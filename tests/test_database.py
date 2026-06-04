import sys
import os
import pytest

# Add uzsl_bot to path so we can import from it
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uzsl_bot"))

import config  # noqa: E402
# Use a temporary database for testing
config.DB_PATH = "test_bot.db"
config.SUPABASE_DB_URL = None  # Force SQLite for testing

from database import (  # noqa: E402
    init_db, get_user, create_user, update_user_profile,
    delete_user_data, save_video, get_user_stats, get_all_labels
)


@pytest.mark.asyncio
async def test_database_workflow():
    # Remove test db if exists
    if os.path.exists("test_bot.db"):
        os.remove("test_bot.db")

    try:
        # Initialize DB
        await init_db()

        # Test labels populated
        labels = await get_all_labels()
        assert len(labels) > 0

        # Test User CRUD
        user_id = 99999
        await create_user(user_id, "testuser", "Test User Name")

        # Verify user created
        user = await get_user(user_id)
        assert user is not None
        assert user["username"] == "testuser"

        # Update user profile
        await update_user_profile(user_id, "18-30", "native", True)
        user = await get_user(user_id)
        assert user["age_group"] == "18-30"
        assert bool(user["is_deaf"]) is True

        # Save a video
        label_id = labels[0]["label_id"]
        video_id = await save_video(
            user_id=user_id,
            label_id=label_id,
            file_id="test_file_id_123",
            duration=3.5,
            file_size=500000,
            width=1280,
            height=720
        )
        assert video_id is not None

        # Verify stats
        stats = await get_user_stats(user_id)
        assert stats["total"] == 1
        assert stats["pending"] == 1

        # Delete user data (GDPR test)
        await delete_user_data(user_id)

        # Verify user and stats deleted
        user = await get_user(user_id)
        assert user is None

        stats = await get_user_stats(user_id)
        assert stats["total"] == 0

    finally:
        # Clean up test database
        if os.path.exists("test_bot.db"):
            os.remove("test_bot.db")
