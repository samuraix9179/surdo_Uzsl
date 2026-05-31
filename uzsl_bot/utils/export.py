import asyncio
import json
import os

import aiohttp
import aiosqlite

from config import DB_PATH, BOT_TOKEN, EXPORT_DIR


async def _fetch_approved():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT v.*, l.word_uz, l.word_ru, l.category
               FROM videos v
               JOIN labels l ON v.label_id = l.label_id
               WHERE v.status = 'approved'
               ORDER BY l.word_uz, v.video_id"""
        )
        return await cursor.fetchall()


async def download_all_approved():
    """Tasdiqlangan videolarni belgi bo'yicha papkalarga yuklab oladi va metadata yozadi."""
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
                "submitted_at": v["submitted_at"],
                "path": os.path.relpath(output_path, EXPORT_DIR),
            })
            print(f"✅ Saved: {output_path}")

    meta_path = os.path.join(EXPORT_DIR, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"\n📦 Jami {len(metadata)} ta video. Metadata: {meta_path}")


if __name__ == "__main__":
    asyncio.run(download_all_approved())
