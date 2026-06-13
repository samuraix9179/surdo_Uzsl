import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

try:
    from huggingface_hub import HfApi, create_repo
except ImportError:
    print("⚠️ Ushbu sinxronizatsiya skriptini ishlatish uchun huggingface_hub-ni o'rnating:")
    print("   pip install huggingface_hub")
    # In test environments we might mock it, so we don't sys.exit if imported as a module
    if __name__ == "__main__":
        sys.exit(1)

# Global tarmoq blokirovkalari (masalan, milliy firewalldan) o'tish uchun rasmiy oyna o'rnatiladi.
os.environ["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")

# Try relative imports, fallback to sys.path manipulation
try:
    from database import (
        get_video_by_id, update_video_s3_url, update_video_landmarks_url,
        get_approved_videos_metadata, get_all_labels, get_sign_variants
    )
    from config import BOT_TOKEN, HF_TOKEN, HUGGINGFACE_REPO, EXPORT_DIR
    from utils.s3_storage import upload_file_to_s3
    from utils.extract_landmarks import process_video
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import (
        get_video_by_id, update_video_s3_url, update_video_landmarks_url,
        get_approved_videos_metadata, get_all_labels, get_sign_variants
    )
    from config import BOT_TOKEN, HF_TOKEN, HUGGINGFACE_REPO, EXPORT_DIR
    try:
        from utils.s3_storage import upload_file_to_s3
        from utils.extract_landmarks import process_video
    except ImportError:
        from s3_storage import upload_file_to_s3  # type: ignore[no-redef]
        from extract_landmarks import process_video  # type: ignore[no-redef]
logger = logging.getLogger(__name__)

# Sozlamalar (.env faylidan o'qiladi)
HF_TOKEN = HF_TOKEN or os.getenv("HUGGINGFACE_TOKEN")
HF_REPO = HUGGINGFACE_REPO or os.getenv("HUGGINGFACE_REPO", "samuraix9179/uzsl-dataset")


def sync_dataset():
    """Yig'ilgan UZSL landmarks va metadata fayllarini Hugging Face'ga sinxronizatsiya qiladi."""
    if not HF_TOKEN:
        print("❌ HUGGINGFACE_TOKEN topilmadi! .env faylida HUGGINGFACE_TOKEN-ni belgilang.")
        print("   Yordam: Hugging Face profilingiz sozlamalaridan 'Write' huquqi bilan Token oling.")
        return

    # Exports papkasi mavjudligini tekshirish
    if not os.path.exists(EXPORT_DIR):
        print(f"❌ '{EXPORT_DIR}' papkasi topilmadi. Avval landmarklarni eksport qiling!")
        return

    print("⚙️ Hugging Face platformasiga sinxronizatsiya boshlandi...")
    api = HfApi(token=HF_TOKEN)

    # 1. Repozitoriya mavjud bo'lmasa, uni yaratadi
    try:
        create_repo(
            repo_id=HF_REPO,
            token=HF_TOKEN,
            repo_type="dataset",
            private=True,  # Boshlang'ichda xavfsizlik uchun yopiq (private) qilamiz
            exist_ok=True
        )
        print(f"✅ Dataset repozitoriyasi tayyor: {HF_REPO}")
    except Exception as e:
        print(f"⚠️ Repozitoriya tekshirishda xato: {e}")

    # 2. Butun exports/landmarks va exports/metadata.json fayllarini yuklash
    try:
        print(f"⏳ Fayllar yuklanmoqda (yo'nalish: {EXPORT_DIR} ──► {HF_REPO}) ...")

        # Metadata.json ni alohida yuklaymiz
        meta_path = os.path.join(EXPORT_DIR, "metadata.json")
        if os.path.exists(meta_path):
            api.upload_file(
                path_or_fileobj=meta_path,
                path_in_repo="metadata.json",
                repo_id=HF_REPO,
                repo_type="dataset"
            )
            print("   └─ ✅ metadata.json yuklandi.")

        # Landmarklar papkasini to'liq yuklaymiz
        landmarks_path = os.path.join(EXPORT_DIR, "landmarks")
        if os.path.exists(landmarks_path):
            api.upload_folder(
                folder_path=landmarks_path,
                path_in_repo="landmarks",
                repo_id=HF_REPO,
                repo_type="dataset"
            )
            print("   └─ ✅ barcha landmark JSON fayllari yuklandi.")

        print("\n🎉 Muvaffaqiyatli yakunlandi! UZSL dataset Hugging Face-ga yuklandi.")
        print(f"🔗 Dataset havolasi: https://huggingface.co/datasets/{HF_REPO}")

    except Exception as e:
        print(f"\n❌ Yuklashda kutilmagan xatolik yuz berdi: {e}")


async def sync_video_to_huggingface(video_id: int) -> bool:
    """Orqa fonda videoni yuklab oladi, landmarklarni ajratadi va HF bucket hamda datasetga yuklaydi."""
    try:
        video = await get_video_by_id(video_id)
        if not video:
            logger.error(f"Video {video_id} not found in database.")
            return False

        word_uz = video["word_uz"]
        category = video["category"] or "other"
        user_id = video["user_id"]

        # local papkalarni yaratish
        video_dir = os.path.join(EXPORT_DIR, "videos", category)
        landmarks_dir = os.path.join(EXPORT_DIR, "landmarks", category)
        os.makedirs(video_dir, exist_ok=True)
        os.makedirs(landmarks_dir, exist_ok=True)

        filename = f"{word_uz}_{video_id}_{user_id}"
        local_video_path = os.path.join(video_dir, f"{filename}.mp4")
        local_landmarks_path = os.path.join(landmarks_dir, f"{filename}.json")

        # 1. Telegramdan yuklab olish (agar lokalda bo'lmasa)
        if not os.path.exists(local_video_path):
            if not BOT_TOKEN:
                logger.error("BOT_TOKEN is not configured.")
                return False
            bot = Bot(token=BOT_TOKEN)
            file = await bot.get_file(video["telegram_file_id"])
            await file.download_to_drive(local_video_path)

        # 2. Landmarklarni ajratish
        # process_video sinxron bo'lgani uchun to_thread da bajaramiz
        sequence = await asyncio.to_thread(process_video, local_video_path)

        payload = {
            "metadata": {
                "video_id": video["video_id"],
                "user_id": video["user_id"],
                "word_uz": video["word_uz"],
                "word_ru": video["word_ru"],
                "category": video["category"],
                "duration_seconds": video["duration_seconds"],
                "file_size_bytes": video["file_size_bytes"],
                "width": video["width"],
                "height": video["height"],
                "submitted_at": str(video["submitted_at"]),
            },
            "frames_count": len(sequence),
            "sequence": sequence
        }

        with open(local_landmarks_path, "w", encoding="utf-8") as out:
            json.dump(payload, out, ensure_ascii=False, indent=2)

        # 3. S3 Bucketga yuklash
        video_s3_key = f"videos/{category}/{filename}.mp4"
        landmarks_s3_key = f"landmarks/{category}/{filename}.json"

        video_s3_url = await upload_file_to_s3(local_video_path, video_s3_key)
        landmarks_s3_url = await upload_file_to_s3(local_landmarks_path, landmarks_s3_key)

        # Bazani yangilash
        if video_s3_url:
            await update_video_s3_url(video_id, video_s3_url)
        if landmarks_s3_url:
            await update_video_landmarks_url(video_id, landmarks_s3_url)

        # 4. Glossary va Dataset Info yangilash hamda HF ga push qilish
        await update_glossary_and_dataset_info()

        return True
    except Exception as e:
        logger.error(f"Error during video syncing: {e}", exc_info=True)
        return False


async def update_glossary_and_dataset_info():
    """Barcha tasdiqlangan/annotatsiya qilingan ma'lumotlar bilan
    glossary.json va dataset_info.json ni yangilaydi.
    """
    try:
        # Hamma approved videolarni olish
        approved_videos = await get_approved_videos_metadata()
        all_labels = await get_all_labels()

        # glossary.json - barcha so'zlar ro'yxati, annotatsiyasi va variantlari bilan
        glossary = []
        categories_count = {}

        for label in all_labels:
            ld = dict(label)
            label_id = ld["label_id"]

            # Variantlarni olish
            variants_db = await get_sign_variants(label_id)
            variants = []
            for var in variants_db:
                vd = dict(var)
                variants.append({
                    "region": vd["region"],
                    "video_file_id": vd["video_file_id"],
                    "notes": vd["notes"]
                })

            glossary.append({
                "label_id": ld["label_id"],
                "word_uz": ld["word_uz"],
                "word_ru": ld.get("word_ru"),
                "word_en": ld.get("word_en"),
                "gloss": ld.get("gloss"),
                "category": ld["category"],
                "target_count": ld["target_count"],
                "current_count": ld["current_count"],
                "difficulty": ld.get("difficulty", 1),
                "handshape": ld.get("handshape"),
                "location": ld.get("location"),
                "movement": ld.get("movement"),
                "expression": ld.get("expression"),
                "usage_example": ld.get("usage_example"),
                "variants": variants
            })

            cat = ld["category"] or "other"
            categories_count[cat] = categories_count.get(cat, 0) + 1

        os.makedirs(EXPORT_DIR, exist_ok=True)
        glossary_path = os.path.join(EXPORT_DIR, "glossary.json")
        with open(glossary_path, "w", encoding="utf-8") as f:
            json.dump(glossary, f, ensure_ascii=False, indent=2)

        # dataset_info.json - umumiy statistika
        dataset_info = {
            "total_words": len(all_labels),
            "total_approved_videos": len(approved_videos),
            "categories_count": categories_count,
            "last_updated": datetime.now().isoformat()
        }

        info_path = os.path.join(EXPORT_DIR, "dataset_info.json")
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(dataset_info, f, ensure_ascii=False, indent=2)

        # Hugging Face repo-ga bu metadata fayllarni yuklash
        if HF_TOKEN and HF_REPO:
            api = HfApi(token=HF_TOKEN)

            # Repozitoriyani tekshirib olish yoki yaratish
            try:
                create_repo(
                    repo_id=HF_REPO,
                    token=HF_TOKEN,
                    repo_type="dataset",
                    private=True,
                    exist_ok=True
                )
            except Exception as e:
                logger.warning(f"Failed to check or create repository: {e}")

            # glossary.json yuklash
            try:
                api.upload_file(
                    path_or_fileobj=glossary_path,
                    path_in_repo="glossary.json",
                    repo_id=HF_REPO,
                    repo_type="dataset"
                )
            except Exception as e:
                logger.error(f"Failed to upload glossary.json: {e}")

            # dataset_info.json yuklash
            try:
                api.upload_file(
                    path_or_fileobj=info_path,
                    path_in_repo="dataset_info.json",
                    repo_id=HF_REPO,
                    repo_type="dataset"
                )
            except Exception as e:
                logger.error(f"Failed to upload dataset_info.json: {e}")

    except Exception as e:
        logger.error(f"Failed to update glossary or dataset info: {e}", exc_info=True)


if __name__ == "__main__":
    sync_dataset()
