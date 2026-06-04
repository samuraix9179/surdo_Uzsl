import asyncio
import json
import os
import sys

import aiohttp

# Add parent dir to path so we can import from database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import _connect  # noqa: E402
from config import BOT_TOKEN, EXPORT_DIR  # noqa: E402


async def _fetch_approved():
    db = await _connect()
    try:
        cursor = await db.execute(
            """SELECT v.*, l.word_uz, l.word_ru, l.category
               FROM videos v
               JOIN labels l ON v.label_id = l.label_id
               WHERE v.status = 'approved'
               ORDER BY l.word_uz, v.video_id"""
        )
        return await cursor.fetchall()
    finally:
        await db.close()


try:
    from utils.s3_storage import upload_file_to_s3
    from utils.sync_to_huggingface import sync_dataset
except ImportError:
    from s3_storage import upload_file_to_s3
    from sync_to_huggingface import sync_dataset


async def download_all_approved():
    """Tasdiqlangan videolarni belgi bo'yicha papkalarga yuklab oladi, HF Bucketga yuklaydi va metadata yozadi."""
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi. .env faylini tekshiring.")

    os.makedirs(EXPORT_DIR, exist_ok=True)
    videos = await _fetch_approved()

    if not videos:
        print("Tasdiqlangan video yo'q.")
        return

    metadata = []
    async with aiohttp.ClientSession() as session:
        for v in videos:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={v['telegram_file_id']}"
            async with session.get(url) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    print(f"⚠️ file_id olinmadi: video_id={v['video_id']}")
                    continue
                file_path = data["result"]["file_path"]

            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            label_dir = os.path.join(EXPORT_DIR, v["word_uz"])
            os.makedirs(label_dir, exist_ok=True)
            filename = f"{v['video_id']}_{v['user_id']}.mp4"
            output_path = os.path.join(label_dir, filename)

            async with session.get(file_url) as resp:
                content = await resp.read()
                with open(output_path, "wb") as f:
                    f.write(content)

            # S3-ga yuklash (Hugging Face Bucket)
            s3_key = f"videos/{v['word_uz']}/{filename}"
            s3_url = await upload_file_to_s3(output_path, s3_key)

            metadata.append({
                "video_id": v["video_id"],
                "user_id": v["user_id"],
                "word_uz": v["word_uz"],
                "word_ru": v["word_ru"],
                "category": v["category"],
                "duration_seconds": v["duration_seconds"],
                "file_size_bytes": v["file_size_bytes"],
                "width": v["width"],
                "height": v["height"],
                "submitted_at": str(v["submitted_at"]),
                "path": os.path.relpath(output_path, EXPORT_DIR),
                "s3_url": s3_url,
            })
            print(f"✅ Saved & Uploaded S3: {output_path} -> {s3_url or 'Failed'}")

    meta_path = os.path.join(EXPORT_DIR, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"\n📦 Jami {len(metadata)} ta video. Metadata: {meta_path}")

    # Landmarklar va metadatalarni Hugging Face Dataset-ga sinxronlash
    try:
        print("\n⏳ Hugging Face Datasetga sinxronizatsiya boshlandi...")
        sync_dataset()
    except Exception as e:
        print(f"⚠️ Hugging Face Datasetga yuklashda xatolik: {e}")


if __name__ == "__main__":
    asyncio.run(download_all_approved())
