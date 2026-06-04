import aiosqlite

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    age_group TEXT,
    uzsl_level TEXT,
    is_deaf BOOLEAN DEFAULT 0,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    videos_submitted INTEGER DEFAULT 0,
    videos_approved INTEGER DEFAULT 0,
    is_admin BOOLEAN DEFAULT 0,
    is_blocked BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS labels (
    label_id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_uz TEXT NOT NULL UNIQUE,
    word_ru TEXT,
    category TEXT,
    example_video_id TEXT,
    target_count INTEGER DEFAULT 50,
    current_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS videos (
    video_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    label_id INTEGER NOT NULL,
    telegram_file_id TEXT NOT NULL,
    duration_seconds REAL,
    file_size_bytes INTEGER,
    width INTEGER,
    height INTEGER,
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    moderator_id INTEGER,
    moderated_at DATETIME,
    rejection_reason TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (label_id) REFERENCES labels(label_id)
);

CREATE TABLE IF NOT EXISTS achievements (
    achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    badge_name TEXT NOT NULL,
    earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
CREATE INDEX IF NOT EXISTS idx_videos_user ON videos(user_id);
CREATE INDEX IF NOT EXISTS idx_videos_label ON videos(label_id);
"""

# Boshlang'ich belgilar (MVP uchun 30 ta)
INITIAL_LABELS = [
    ("salom", "привет", "salomlashish"),
    ("xayr", "пока", "salomlashish"),
    ("rahmat", "спасибо", "salomlashish"),
    ("kechirasiz", "извините", "salomlashish"),
    ("ha", "да", "javob"),
    ("yo'q", "нет", "javob"),
    ("nima", "что", "savol"),
    ("qancha", "сколько", "savol"),
    ("qayerda", "где", "savol"),
    ("qachon", "когда", "savol"),
    ("kim", "кто", "savol"),
    ("yordam", "помощь", "yordam"),
    ("uy", "дом", "joy"),
    ("do'kon", "магазин", "joy"),
    ("avtobus", "автобус", "joy"),
    ("shifoxona", "больница", "joy"),
    ("bormoq", "идти", "harakat"),
    ("kelmoq", "приходить", "harakat"),
    ("olmoq", "брать", "harakat"),
    ("bermoq", "давать", "harakat"),
    ("non", "хлеб", "tovar"),
    ("suv", "вода", "tovar"),
    ("sut", "молоко", "tovar"),
    ("pul", "деньги", "tovar"),
    ("bugun", "сегодня", "vaqt"),
    ("ertaga", "завтра", "vaqt"),
    ("kecha", "вчера", "vaqt"),
    ("yaxshi", "хорошо", "his"),
    ("yomon", "плохо", "his"),
    ("og'rimoq", "болеть", "his"),
]


async def _connect():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA journal_mode = WAL")
    return db


async def init_db(admin_ids=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode = WAL")
        await db.executescript(SCHEMA)

        cursor = await db.execute("SELECT COUNT(*) FROM labels")
        count = (await cursor.fetchone())[0]
        if count == 0:
            await db.executemany(
                "INSERT INTO labels (word_uz, word_ru, category) VALUES (?, ?, ?)",
                INITIAL_LABELS,
            )
        await db.commit()


# ------------------- USERS -------------------

async def get_user(user_id: int):
    db = await _connect()
    try:
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()
    finally:
        await db.close()


async def create_user(user_id: int, username: str, full_name: str):
    db = await _connect()
    try:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name),
        )
        await db.commit()
    finally:
        await db.close()


async def update_user_profile(user_id: int, age_group: str, uzsl_level: str, is_deaf: bool):
    db = await _connect()
    try:
        await db.execute(
            "UPDATE users SET age_group = ?, uzsl_level = ?, is_deaf = ? WHERE user_id = ?",
            (age_group, uzsl_level, is_deaf, user_id),
        )
        await db.commit()
    finally:
        await db.close()


async def get_all_user_ids(only_active: bool = True):
    db = await _connect()
    try:
        query = "SELECT user_id FROM users"
        if only_active:
            query += " WHERE is_blocked = 0"
        cursor = await db.execute(query)
        return [row["user_id"] for row in await cursor.fetchall()]
    finally:
        await db.close()


async def set_user_blocked(user_id: int, blocked: bool):
    db = await _connect()
    try:
        await db.execute(
            "UPDATE users SET is_blocked = ? WHERE user_id = ?",
            (1 if blocked else 0, user_id),
        )
        await db.commit()
    finally:
        await db.close()


async def delete_user_data(user_id: int):
    """Foydalanuvchi va uning barcha videolarini o'chiradi (GDPR)."""
    db = await _connect()
    try:
        # Belgilar hisoblagichini tuzatish (faqat pending/approved videolar uchun)
        cursor = await db.execute(
            "SELECT label_id FROM videos WHERE user_id = ? AND status != 'rejected'",
            (user_id,),
        )
        label_ids = [row["label_id"] for row in await cursor.fetchall()]
        for lid in label_ids:
            await db.execute(
                "UPDATE labels SET current_count = MAX(0, current_count - 1) WHERE label_id = ?",
                (lid,),
            )

        await db.execute("DELETE FROM videos WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM achievements WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()
    finally:
        await db.close()


# ------------------- LABELS -------------------

async def get_labels_needing_videos(limit: int = 10):
    """Eng kam video bor belgilarni qaytaradi."""
    db = await _connect()
    try:
        cursor = await db.execute(
            """SELECT * FROM labels
               WHERE is_active = 1 AND current_count < target_count
               ORDER BY current_count ASC, word_uz ASC
               LIMIT ?""",
            (limit,),
        )
        return await cursor.fetchall()
    finally:
        await db.close()


async def get_all_labels():
    db = await _connect()
    try:
        cursor = await db.execute(
            "SELECT * FROM labels ORDER BY current_count ASC, word_uz ASC"
        )
        return await cursor.fetchall()
    finally:
        await db.close()


async def get_label_by_id(label_id: int):
    db = await _connect()
    try:
        cursor = await db.execute("SELECT * FROM labels WHERE label_id = ?", (label_id,))
        return await cursor.fetchone()
    finally:
        await db.close()


from typing import Optional

async def add_label(word_uz: str, word_ru: Optional[str] = None, category: Optional[str] = None, target_count: int = 50):
    db = await _connect()
    try:
        await db.execute(
            "INSERT INTO labels (word_uz, word_ru, category, target_count) VALUES (?, ?, ?, ?)",
            (word_uz, word_ru, category, target_count),
        )
        await db.commit()
    finally:
        await db.close()


async def set_example_video(label_id: int, file_id: str):
    db = await _connect()
    try:
        await db.execute(
            "UPDATE labels SET example_video_id = ? WHERE label_id = ?",
            (file_id, label_id),
        )
        await db.commit()
    finally:
        await db.close()


async def get_labels_by_category(category: str, limit: int = 10):
    db = await _connect()
    try:
        cursor = await db.execute(
            """SELECT * FROM labels
               WHERE is_active = 1 AND category = ? AND current_count < target_count
               ORDER BY current_count ASC, word_uz ASC
               LIMIT ?""",
            (category, limit),
        )
        return await cursor.fetchall()
    finally:
        await db.close()


async def get_or_create_custom_label(word_uz: str, target_count: int = 50) -> int:
    db = await _connect()
    try:
        word_uz = word_uz.strip().lower()
        cursor = await db.execute("SELECT label_id FROM labels WHERE word_uz = ?", (word_uz,))
        row = await cursor.fetchone()
        if row:
            return row["label_id"]

        cursor = await db.execute(
            "INSERT INTO labels (word_uz, category, target_count) VALUES (?, 'erkin_tarjima', ?)",
            (word_uz, target_count),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


# ------------------- VIDEOS -------------------

async def save_video(user_id: int, label_id: int, file_id: str,
                     duration: float, file_size: int, width: int, height: int) -> int:
    db = await _connect()
    try:
        cursor = await db.execute(
            """INSERT INTO videos
               (user_id, label_id, telegram_file_id, duration_seconds,
                file_size_bytes, width, height)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, label_id, file_id, duration, file_size, width, height),
        )
        video_id = cursor.lastrowid
        await db.execute(
            "UPDATE users SET videos_submitted = videos_submitted + 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.execute(
            "UPDATE labels SET current_count = current_count + 1 WHERE label_id = ?",
            (label_id,),
        )
        await db.commit()
        return video_id
    finally:
        await db.close()


async def get_user_stats(user_id: int):
    db = await _connect()
    try:
        cursor = await db.execute(
            """SELECT COUNT(*) as total,
                      SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                      SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                      SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
               FROM videos WHERE user_id = ?""",
            (user_id,),
        )
        return await cursor.fetchone()
    finally:
        await db.close()


async def get_leaderboard(limit: int = 10):
    db = await _connect()
    try:
        cursor = await db.execute(
            """SELECT full_name, videos_submitted, videos_approved
               FROM users
               WHERE videos_submitted > 0
               ORDER BY videos_approved DESC, videos_submitted DESC
               LIMIT ?""",
            (limit,),
        )
        return await cursor.fetchall()
    finally:
        await db.close()


async def get_pending_videos(limit: int = 1):
    db = await _connect()
    try:
        cursor = await db.execute(
            """SELECT v.*, l.word_uz, u.full_name as user_name
               FROM videos v
               JOIN labels l ON v.label_id = l.label_id
               JOIN users u ON v.user_id = u.user_id
               WHERE v.status = 'pending'
               ORDER BY v.submitted_at ASC
               LIMIT ?""",
            (limit,),
        )
        return await cursor.fetchall()
    finally:
        await db.close()


async def get_video_owner(video_id: int):
    db = await _connect()
    try:
        cursor = await db.execute(
            "SELECT user_id FROM videos WHERE video_id = ?", (video_id,)
        )
        row = await cursor.fetchone()
        return row["user_id"] if row else None
    finally:
        await db.close()


async def moderate_video(video_id: int, status: str, moderator_id: int, reason: Optional[str] = None):
    db = await _connect()
    try:
        await db.execute(
            """UPDATE videos
               SET status = ?, moderator_id = ?,
                   moderated_at = CURRENT_TIMESTAMP, rejection_reason = ?
               WHERE video_id = ?""",
            (status, moderator_id, reason, video_id),
        )
        if status == "approved":
            cursor = await db.execute(
                "SELECT user_id FROM videos WHERE video_id = ?", (video_id,)
            )
            row = await cursor.fetchone()
            if row:
                await db.execute(
                    "UPDATE users SET videos_approved = videos_approved + 1 WHERE user_id = ?",
                    (row["user_id"],),
                )
        elif status == "rejected":
            # Rad etilgan video belgisining hisoblagichini kamaytirish
            cursor = await db.execute(
                "SELECT label_id FROM videos WHERE video_id = ?", (video_id,)
            )
            row = await cursor.fetchone()
            if row:
                await db.execute(
                    "UPDATE labels SET current_count = MAX(0, current_count - 1) WHERE label_id = ?",
                    (row["label_id"],),
                )
        await db.commit()
    finally:
        await db.close()


# ------------------- ACHIEVEMENTS -------------------

async def get_user_badges(user_id: int):
    db = await _connect()
    try:
        cursor = await db.execute(
            "SELECT badge_name FROM achievements WHERE user_id = ?", (user_id,)
        )
        return {row["badge_name"] for row in await cursor.fetchall()}
    finally:
        await db.close()


async def add_achievement(user_id: int, badge_name: str):
    db = await _connect()
    try:
        await db.execute(
            "INSERT INTO achievements (user_id, badge_name) VALUES (?, ?)",
            (user_id, badge_name),
        )
        await db.commit()
    finally:
        await db.close()


# ------------------- STATS / EXPORT -------------------

async def get_global_stats():
    db = await _connect()
    try:
        stats = {}
        cursor = await db.execute("SELECT COUNT(*) AS c FROM users")
        stats["users"] = (await cursor.fetchone())["c"]

        cursor = await db.execute(
            """SELECT
                 COUNT(*) AS total,
                 SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved,
                 SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
                 SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS rejected
               FROM videos"""
        )
        row = await cursor.fetchone()
        stats["videos_total"] = row["total"] or 0
        stats["videos_approved"] = row["approved"] or 0
        stats["videos_pending"] = row["pending"] or 0
        stats["videos_rejected"] = row["rejected"] or 0

        cursor = await db.execute(
            "SELECT COUNT(*) AS c FROM labels WHERE current_count >= target_count"
        )
        stats["labels_done"] = (await cursor.fetchone())["c"]
        cursor = await db.execute("SELECT COUNT(*) AS c FROM labels")
        stats["labels_total"] = (await cursor.fetchone())["c"]

        return stats
    finally:
        await db.close()


async def get_label_distribution():
    db = await _connect()
    try:
        cursor = await db.execute(
            "SELECT word_uz, current_count, target_count FROM labels ORDER BY current_count ASC"
        )
        return await cursor.fetchall()
    finally:
        await db.close()


async def get_approved_videos_metadata():
    db = await _connect()
    try:
        cursor = await db.execute(
            """SELECT v.video_id, v.user_id, v.telegram_file_id, v.duration_seconds,
                      v.file_size_bytes, v.width, v.height, v.submitted_at,
                      l.word_uz, l.word_ru, l.category
               FROM videos v
               JOIN labels l ON v.label_id = l.label_id
               WHERE v.status = 'approved'
               ORDER BY l.word_uz, v.video_id"""
        )
        return await cursor.fetchall()
    finally:
        await db.close()
