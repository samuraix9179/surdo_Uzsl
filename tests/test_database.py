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
    delete_user_data, save_video, get_user_stats, get_all_labels,
    get_video_by_id, update_video_s3_url, update_video_landmarks_url,
    add_sign_variant, get_sign_variants, update_label_annotation,
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


@pytest.mark.asyncio
async def test_labels_expanded_to_100_plus():
    """100+ ta so'z yuklanganligi va kategoriyalar to'g'riligini tekshiradi."""
    if os.path.exists("test_bot.db"):
        os.remove("test_bot.db")
    try:
        await init_db()
        labels = await get_all_labels()
        # Kamida 100 ta so'z bo'lishi kerak
        assert len(labels) >= 100, f"Faqat {len(labels)} ta so'z topildi, kamida 100 ta bo'lishi kerak"

        # Barcha kategoriyalar mavjudligini tekshirish
        categories = {lb["category"] for lb in labels}
        required_cats = {"muloqot", "savol", "javob", "oila", "sonlar", "vaqt",
                         "joy", "harakat", "ovqat", "his", "ranglar", "transport", "yordam"}
        missing = required_cats - categories
        assert not missing, f"Quyidagi kategoriyalar yo'q: {missing}"
    finally:
        if os.path.exists("test_bot.db"):
            os.remove("test_bot.db")


@pytest.mark.asyncio
async def test_get_video_by_id():
    """get_video_by_id funksiyasi video, label va user ma'lumotlarini qaytarishini tekshiradi."""
    if os.path.exists("test_bot.db"):
        os.remove("test_bot.db")
    try:
        await init_db()
        labels = await get_all_labels()
        label_id = labels[0]["label_id"]

        # Test user va video yaratish
        await create_user(88888, "testuser2", "Test User 2")
        await update_user_profile(88888, "18-30", "beginner", False)
        video_id = await save_video(
            user_id=88888, label_id=label_id, file_id="file_test_001",
            duration=4.0, file_size=600000, width=1920, height=1080
        )

        # Video ma'lumotlarini olish
        video = await get_video_by_id(video_id)
        assert video is not None
        assert video["video_id"] == video_id
        assert video["telegram_file_id"] == "file_test_001"
        assert video["word_uz"] == labels[0]["word_uz"]
    finally:
        if os.path.exists("test_bot.db"):
            os.remove("test_bot.db")


@pytest.mark.asyncio
async def test_update_video_s3_url_and_landmarks():
    """Video uchun s3_url va landmarks_url saqlash va o'qishni tekshiradi."""
    if os.path.exists("test_bot.db"):
        os.remove("test_bot.db")
    try:
        await init_db()
        labels = await get_all_labels()
        label_id = labels[0]["label_id"]

        await create_user(77777, "testuser3", "Test User 3")
        video_id = await save_video(
            user_id=77777, label_id=label_id, file_id="file_test_002",
            duration=3.0, file_size=400000, width=1280, height=720
        )

        # s3_url yangilash
        test_url = "https://huggingface.co/datasets/test/resolve/main/videos/salom/1.mp4"
        await update_video_s3_url(video_id, test_url)

        video = await get_video_by_id(video_id)
        assert video["s3_url"] == test_url

        # landmarks_url yangilash
        lm_url = "https://huggingface.co/datasets/test/resolve/main/landmarks/salom/1.json"
        await update_video_landmarks_url(video_id, lm_url)

        video = await get_video_by_id(video_id)
        assert video["landmarks_url"] == lm_url
    finally:
        if os.path.exists("test_bot.db"):
            os.remove("test_bot.db")


@pytest.mark.asyncio
async def test_sign_variants():
    """Hududiy variantlar qo'shish va olish."""
    if os.path.exists("test_bot.db"):
        os.remove("test_bot.db")
    try:
        await init_db()
        labels = await get_all_labels()
        label_id = labels[0]["label_id"]

        # Variant qo'shish
        await add_sign_variant(label_id, "Toshkent", "tashkent_video_001", "Standart variant")
        await add_sign_variant(label_id, "Andijon", "andijon_video_001", "Hududiy farq bor")

        # Variantlarni olish
        variants = await get_sign_variants(label_id)
        assert len(variants) == 2
        regions = {v["region"] for v in variants}
        assert "Toshkent" in regions
        assert "Andijon" in regions
    finally:
        if os.path.exists("test_bot.db"):
            os.remove("test_bot.db")


@pytest.mark.asyncio
async def test_update_label_annotation():
    """Label uchun annotatsiya maydonlarini yangilash."""
    if os.path.exists("test_bot.db"):
        os.remove("test_bot.db")
    try:
        await init_db()
        labels = await get_all_labels()
        label_id = labels[0]["label_id"]

        # Annotatsiyani yangilash
        await update_label_annotation(
            label_id=label_id,
            handshape="flat_hand",
            location="head",
            movement="outward",
            expression="neutral",
            usage_example="Salom, qalaysiz?"
        )

        # Tekshirish
        from database import get_label_by_id  # noqa: E402
        label = await get_label_by_id(label_id)
        assert label["handshape"] == "flat_hand"
        assert label["location"] == "head"
        assert label["movement"] == "outward"
        assert label["expression"] == "neutral"
        assert label["usage_example"] == "Salom, qalaysiz?"
    finally:
        if os.path.exists("test_bot.db"):
            os.remove("test_bot.db")
