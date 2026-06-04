import asyncio
import logging
import os
import sys
import tempfile
import cv2
import mediapipe as mp
from telegram import Bot

# Add parent directory to path to import database and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BOT_TOKEN  # noqa: E402
from database import moderate_video, get_video_owner  # noqa: E402

logger = logging.getLogger(__name__)


def analyze_video_quality_sync(video_path: str) -> dict:
    """MediaPipe Holistic yordamida videoda yuz va qo'llar ko'rinishini tahlil qiladi."""
    if not os.path.exists(video_path):
        return {"ok": False, "reason": "Video file not found", "rejection_reason": "other"}

    mp_holistic = mp.solutions.holistic
    cap = cv2.VideoCapture(video_path)

    total_frames = 0
    face_detected_frames = 0
    left_hand_detected_frames = 0
    right_hand_detected_frames = 0

    # model_complexity=0 tezlik uchun, CPU resurslarini tejaydi
    with mp_holistic.Holistic(
        static_image_mode=False,
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as holistic:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            total_frames += 1
            try:
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = holistic.process(image)

                if results.face_landmarks is not None:
                    face_detected_frames += 1
                if results.left_hand_landmarks is not None:
                    left_hand_detected_frames += 1
                if results.right_hand_landmarks is not None:
                    right_hand_detected_frames += 1
            except Exception as e:
                logger.error(f"Error processing frame {total_frames}: {e}")

    cap.release()

    if total_frames == 0:
        return {"ok": False, "reason": "Video kadrlarini o'qib bo'lmadi", "rejection_reason": "blurry"}

    face_ratio = face_detected_frames / total_frames
    left_hand_ratio = left_hand_detected_frames / total_frames
    right_hand_ratio = right_hand_detected_frames / total_frames

    # Yuz kamida 70% kadrda bo'lishi kerak, qo'llardan biri kamida 30% kadrda bo'lishi kerak
    face_ok = face_ratio >= 0.70
    hand_ok = (left_hand_ratio >= 0.30 or right_hand_ratio >= 0.30)

    is_valid = face_ok and hand_ok
    rejection_reason = None
    if not is_valid:
        if not face_ok:
            rejection_reason = "incomplete"  # Yuz yoki yelka to'liq ko'rinmayapti
        elif not hand_ok:
            rejection_reason = "incomplete"  # Qo'l to'liq ko'rinmayapti

    return {
        "ok": is_valid,
        "face_ratio": face_ratio,
        "left_hand_ratio": left_hand_ratio,
        "right_hand_ratio": right_hand_ratio,
        "rejection_reason": rejection_reason,
        "total_frames": total_frames
    }


async def analyze_video_quality(video_path: str) -> dict:
    return await asyncio.to_thread(analyze_video_quality_sync, video_path)


async def auto_moderate_video(video_id: int, telegram_file_id: str, label_word: str):
    """Orqa fonda videoni yuklab olib, MediaPipe orqali avtomatik tahlil qiladi va kerak bo'lsa rad etadi."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not configured.")
        return

    bot = Bot(token=BOT_TOKEN)
    temp_dir = os.path.join("data", "temp")
    os.makedirs(temp_dir, exist_ok=True)

    # Vaqtinchalik fayl yaratamiz
    with tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".mp4", delete=False) as tf:
        temp_file_path = tf.name

    try:
        # Telegramdan videoni yuklab olamiz
        logger.info(f"Downloading video {video_id} for auto-moderation...")
        file = await bot.get_file(telegram_file_id)
        await file.download_to_drive(temp_file_path)

        # Video sifatini tahlil qilamiz
        logger.info(f"Analyzing video quality for video {video_id}...")
        analysis = await analyze_video_quality(temp_file_path)

        # Agar tahlil natijasida video sifatsiz chiqsa
        if not analysis["ok"]:
            reason = analysis["rejection_reason"] or "incomplete"
            logger.info(f"Auto-moderator: Rejecting video {video_id} (reason: {reason})")

            # Moderatsiya holatini bazada rejected qilish (moderator_id=0 AI moderator degani)
            await moderate_video(video_id=video_id, status="rejected", moderator_id=0, reason=reason)

            # Foydalanuvchiga xabar beramiz
            user_id = await get_video_owner(video_id)
            if user_id:
                reason_text = "Qo'l/yelka to'liq ko'rinmayapti yoki yorug'lik yetarli emas"
                if reason == "dark":
                    reason_text = "Yorug'lik yetarli emas (yuzingiz qorong'uda qolgan)"

                rejection_msg = (
                    f"⚠️ *Videongiz avtomatik tekshiruvdan o'ta olmadi (Rad etildi):*\n\n"
                    f"• Belgi: *{label_word}*\n"
                    f"• Sababi: *{reason_text}*\n\n"
                    f"Iltimos, yorug'roq joyda turib, qo'llaringiz va yuzingiz kameraga to'liq "
                    f"ko'rinadigan qilib videoni qaytadan yozib yuboring. 📹"
                )
                try:
                    await bot.send_message(chat_id=user_id, text=rejection_msg, parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Failed to send message to user {user_id}: {e}")
        else:
            logger.info(f"Auto-moderator: Video {video_id} passed basic checks. Pending manual review.")

    except Exception as e:
        logger.error(f"Error during auto-moderation for video {video_id}: {e}")
    finally:
        # Vaqtinchalik faylni o'chiramiz
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.error(f"Failed to remove temp file: {e}")
