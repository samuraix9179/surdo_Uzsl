import aiosqlite
import asyncpg
from typing import Optional, Tuple

from config import DB_PATH, SUPABASE_DB_URL

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
    word_en TEXT,
    gloss TEXT,
    category TEXT,
    example_video_id TEXT,
    target_count INTEGER DEFAULT 50,
    current_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    difficulty INTEGER DEFAULT 1,
    handshape TEXT,
    location TEXT,
    movement TEXT,
    expression TEXT,
    usage_example TEXT
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
    s3_url TEXT,
    landmarks_url TEXT,
    annotation_notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (label_id) REFERENCES labels(label_id)
);

CREATE TABLE IF NOT EXISTS sign_variants (
    variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
    label_id INTEGER NOT NULL,
    region TEXT NOT NULL,
    video_file_id TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
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

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    age_group TEXT,
    uzsl_level TEXT,
    is_deaf BOOLEAN DEFAULT FALSE,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    videos_submitted INTEGER DEFAULT 0,
    videos_approved INTEGER DEFAULT 0,
    is_admin BOOLEAN DEFAULT FALSE,
    is_blocked BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS labels (
    label_id SERIAL PRIMARY KEY,
    word_uz TEXT NOT NULL UNIQUE,
    word_ru TEXT,
    word_en TEXT,
    gloss TEXT,
    category TEXT,
    example_video_id TEXT,
    target_count INTEGER DEFAULT 50,
    current_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    difficulty INTEGER DEFAULT 1,
    handshape TEXT,
    location TEXT,
    movement TEXT,
    expression TEXT,
    usage_example TEXT
);

CREATE TABLE IF NOT EXISTS videos (
    video_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    label_id INTEGER NOT NULL,
    telegram_file_id TEXT NOT NULL,
    duration_seconds REAL,
    file_size_bytes BIGINT,
    width INTEGER,
    height INTEGER,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    moderator_id BIGINT,
    moderated_at TIMESTAMP,
    rejection_reason TEXT,
    s3_url TEXT,
    landmarks_url TEXT,
    annotation_notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (label_id) REFERENCES labels(label_id)
);

CREATE TABLE IF NOT EXISTS sign_variants (
    variant_id SERIAL PRIMARY KEY,
    label_id INTEGER NOT NULL,
    region TEXT NOT NULL,
    video_file_id TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (label_id) REFERENCES labels(label_id)
);

CREATE TABLE IF NOT EXISTS achievements (
    achievement_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    badge_name TEXT NOT NULL,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
CREATE INDEX IF NOT EXISTS idx_videos_user ON videos(user_id);
CREATE INDEX IF NOT EXISTS idx_videos_label ON videos(label_id);
"""


# Boshlang'ich belgilar — to'liq multimedia lug'at (120+ ta so'z)
# Format: (word_uz, word_ru, category)
INITIAL_LABELS = [
    # --- Muloqot / Salomlashish (10) ---
    ("salom", "привет", "muloqot"),
    ("xayr", "пока", "muloqot"),
    ("rahmat", "спасибо", "muloqot"),
    ("kechirasiz", "извините", "muloqot"),
    ("marhamat", "пожалуйста", "muloqot"),
    ("assalomu alaykum", "мир вам", "muloqot"),
    ("xush kelibsiz", "добро пожаловать", "muloqot"),
    ("ko'rishguncha", "до встречи", "muloqot"),
    ("qandaysiz", "как дела", "muloqot"),
    ("yaxshi", "хорошо", "muloqot"),

    # --- Savollar (10) ---
    ("nima", "что", "savol"),
    ("kim", "кто", "savol"),
    ("qayerda", "где", "savol"),
    ("qachon", "когда", "savol"),
    ("qanday", "какой/как", "savol"),
    ("nima uchun", "почему", "savol"),
    ("qancha", "сколько", "savol"),
    ("qaysi", "который", "savol"),
    ("bormi", "есть ли", "savol"),
    ("mumkinmi", "можно ли", "savol"),

    # --- Javoblar (5) ---
    ("ha", "да", "javob"),
    ("yo'q", "нет", "javob"),
    ("bilmayman", "не знаю", "javob"),
    ("tushundim", "понял", "javob"),
    ("to'g'ri", "правильно", "javob"),

    # --- Oila (10) ---
    ("ona", "мама", "oila"),
    ("ota", "папа", "oila"),
    ("aka", "старший брат", "oila"),
    ("opa", "старшая сестра", "oila"),
    ("bola", "ребёнок", "oila"),
    ("er", "муж", "oila"),
    ("xotin", "жена", "oila"),
    ("buvi", "бабушка", "oila"),
    ("bobo", "дедушка", "oila"),
    ("oila", "семья", "oila"),

    # --- Sonlar (15) ---
    ("nol", "ноль", "sonlar"),
    ("bir", "один", "sonlar"),
    ("ikki", "два", "sonlar"),
    ("uch", "три", "sonlar"),
    ("to'rt", "четыре", "sonlar"),
    ("besh", "пять", "sonlar"),
    ("olti", "шесть", "sonlar"),
    ("yetti", "семь", "sonlar"),
    ("sakkiz", "восемь", "sonlar"),
    ("to'qqiz", "девять", "sonlar"),
    ("o'n", "десять", "sonlar"),
    ("yigirma", "двадцать", "sonlar"),
    ("ellik", "пятьдесят", "sonlar"),
    ("yuz", "сто", "sonlar"),
    ("ming", "тысяча", "sonlar"),

    # --- Vaqt (10) ---
    ("bugun", "сегодня", "vaqt"),
    ("ertaga", "завтра", "vaqt"),
    ("kecha", "вчера", "vaqt"),
    ("hozir", "сейчас", "vaqt"),
    ("soat", "час", "vaqt"),
    ("daqiqa", "минута", "vaqt"),
    ("hafta", "неделя", "vaqt"),
    ("oy", "месяц", "vaqt"),
    ("yil", "год", "vaqt"),
    ("ertalab", "утром", "vaqt"),

    # --- Joylar (10) ---
    ("uy", "дом", "joy"),
    ("do'kon", "магазин", "joy"),
    ("maktab", "школа", "joy"),
    ("shifoxona", "больница", "joy"),
    ("bank", "банк", "joy"),
    ("masjid", "мечеть", "joy"),
    ("bozor", "базар/рынок", "joy"),
    ("restoran", "ресторан", "joy"),
    ("dorixona", "аптека", "joy"),
    ("universitet", "университет", "joy"),

    # --- Harakatlar (15) ---
    ("bormoq", "идти", "harakat"),
    ("kelmoq", "приходить", "harakat"),
    ("olmoq", "брать", "harakat"),
    ("bermoq", "давать", "harakat"),
    ("ko'rmoq", "видеть", "harakat"),
    ("eshitmoq", "слышать", "harakat"),
    ("yemoq", "есть/кушать", "harakat"),
    ("ichmoq", "пить", "harakat"),
    ("o'qimoq", "читать", "harakat"),
    ("yozmoq", "писать", "harakat"),
    ("gapirmoq", "говорить", "harakat"),
    ("ishlamoq", "работать", "harakat"),
    ("o'rganmoq", "учиться", "harakat"),
    ("uxlamoq", "спать", "harakat"),
    ("kutmoq", "ждать", "harakat"),

    # --- Ovqat (10) ---
    ("non", "хлеб", "ovqat"),
    ("go'sht", "мясо", "ovqat"),
    ("sabzavot", "овощи", "ovqat"),
    ("meva", "фрукты", "ovqat"),
    ("guruch", "рис", "ovqat"),
    ("osh", "плов", "ovqat"),
    ("sho'rva", "суп", "ovqat"),
    ("choy", "чай", "ovqat"),
    ("tuz", "соль", "ovqat"),
    ("shakar", "сахар", "ovqat"),

    # --- Tovarlar / Ichimliklar (5) ---
    ("suv", "вода", "tovar"),
    ("sut", "молоко", "tovar"),
    ("dori", "лекарство", "tovar"),
    ("kiyim", "одежда", "tovar"),
    ("telefon", "телефон", "tovar"),

    # --- Pul (5) ---
    ("pul", "деньги", "pul"),
    ("narx", "цена", "pul"),
    ("qancha turadi", "сколько стоит", "pul"),
    ("qimmat", "дорого", "pul"),
    ("arzon", "дешёво", "pul"),

    # --- His-tuyg'ular (10) ---
    ("yaxshi", "хорошо", "his"),
    ("yomon", "плохо", "his"),
    ("og'rimoq", "болеть", "his"),
    ("xursand", "радостный", "his"),
    ("g'amgin", "грустный", "his"),
    ("charchagan", "усталый", "his"),
    ("qo'rqmoq", "бояться", "his"),
    ("sevmoq", "любить", "his"),
    ("xafa", "обиженный", "his"),
    ("hayron", "удивлённый", "his"),

    # --- Ranglar (5) ---
    ("qizil", "красный", "ranglar"),
    ("ko'k", "синий", "ranglar"),
    ("yashil", "зелёный", "ranglar"),
    ("oq", "белый", "ranglar"),
    ("qora", "чёрный", "ranglar"),

    # --- Transport (5) ---
    ("avtobus", "автобус", "transport"),
    ("metro", "метро", "transport"),
    ("taksi", "такси", "transport"),
    ("poyezd", "поезд", "transport"),
    ("samolyot", "самолёт", "transport"),

    # --- Yordam (5) ---
    ("yordam", "помощь", "yordam"),
    ("kerak", "нужно", "yordam"),
    ("tez yordam", "скорая помощь", "yordam"),
    ("politsiya", "полиция", "yordam"),
    ("o't o'chirish", "пожарная", "yordam"),
]


class PGCursor:
    def __init__(self, rows, lastrowid=None):
        self.rows = rows
        self.lastrowid = lastrowid
        self._index = 0

    async def fetchone(self):
        if self._index < len(self.rows):
            row = self.rows[self._index]
            self._index += 1
            return row
        return None

    async def fetchall(self):
        return self.rows


class DBWrapper:
    def __init__(self, conn, is_postgres=False):
        self.conn = conn
        self.is_postgres = is_postgres

    async def execute(self, query: str, params: Optional[tuple] = None):
        query, params = self._translate(query, params)
        if self.is_postgres:
            if "RETURNING" in query.upper():
                rows = await self.conn.fetch(query, *(params or ()))
                lastrowid = rows[0][0] if rows else None
                return PGCursor(rows, lastrowid)
            else:
                if "SELECT" in query.upper():
                    rows = await self.conn.fetch(query, *(params or ()))
                    return PGCursor(rows)
                else:
                    await self.conn.execute(query, *(params or ()))
                    return PGCursor([])
        else:
            cursor = await self.conn.execute(query, params or ())
            return cursor

    async def fetchone(self, query: str, params: Optional[tuple] = None):
        cursor = await self.execute(query, params)
        return await cursor.fetchone()

    async def fetchall(self, query: str, params: Optional[tuple] = None):
        cursor = await self.execute(query, params)
        return await cursor.fetchall()

    async def executemany(self, query: str, params_list: list):
        if self.is_postgres:
            count = query.count("?")
            for i in range(1, count + 1):
                query = query.replace("?", f"${i}", 1)
            await self.conn.executemany(query, params_list)
        else:
            await self.conn.executemany(query, params_list)

    async def commit(self):
        if not self.is_postgres:
            await self.conn.commit()

    async def close(self):
        await self.conn.close()

    def _translate(self, query: str, params: Optional[tuple]) -> Tuple[str, Optional[tuple]]:
        if not self.is_postgres:
            if params:
                new_params = tuple(1 if x is True else (0 if x is False else x) for x in params)
                return query, new_params
            return query, params

        count = query.count("?")
        for i in range(1, count + 1):
            query = query.replace("?", f"${i}", 1)

        if "INSERT OR IGNORE INTO users" in query:
            query = query.replace("INSERT OR IGNORE INTO users", "INSERT INTO users")
            query += " ON CONFLICT (user_id) DO NOTHING"
        elif "INSERT OR IGNORE INTO labels" in query:
            query = query.replace("INSERT OR IGNORE INTO labels", "INSERT INTO labels")
            query += " ON CONFLICT (word_uz) DO NOTHING"

        if "INSERT INTO videos" in query and "RETURNING" not in query.upper():
            query += " RETURNING video_id"
        elif "INSERT INTO labels" in query and "RETURNING" not in query.upper():
            query += " RETURNING label_id"

        return query, params


async def _connect():
    if SUPABASE_DB_URL:
        # Supabase requires SSL for remote connections
        kwargs = {}
        if "supabase.com" in SUPABASE_DB_URL or "sslmode=require" in SUPABASE_DB_URL:
            kwargs["ssl"] = "require"
        
        conn = await asyncpg.connect(SUPABASE_DB_URL, **kwargs)
        return DBWrapper(conn, is_postgres=True)
    else:
        conn = await aiosqlite.connect(DB_PATH)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA journal_mode = WAL")
        return DBWrapper(conn, is_postgres=False)


async def init_db(admin_ids=None):
    db = await _connect()
    try:
        if db.is_postgres:
            await db.conn.execute(POSTGRES_SCHEMA)
        else:
            await db.conn.execute("PRAGMA journal_mode = WAL")
            await db.conn.executescript(SCHEMA)

        # --- Migratsiya: mavjud bazalarga yangi ustunlarni qo'shish ---
        await _run_migrations(db)

        # --- Lug'at so'zlarini yuklash (INSERT OR IGNORE = takrorlanmasligi uchun) ---
        await db.executemany(
            "INSERT OR IGNORE INTO labels (word_uz, word_ru, category) VALUES (?, ?, ?)",
            INITIAL_LABELS,
        )

        # Gloss ustunini avtomatik to'ldirish (UPPER(word_uz))
        if db.is_postgres:
            await db.conn.execute(
                "UPDATE labels SET gloss = UPPER(word_uz) WHERE gloss IS NULL"
            )
        else:
            await db.execute(
                "UPDATE labels SET gloss = UPPER(word_uz) WHERE gloss IS NULL"
            )

        await db.commit()
    finally:
        await db.close()


async def _run_migrations(db):
    """Mavjud bazalarga yangi ustunlarni qo'shadi. Agar ustun allaqachon bo'lsa — o'tkazib yuboradi."""
    # labels jadvaliga yangi ustunlar
    label_columns = [
        ("word_en", "TEXT"),
        ("gloss", "TEXT"),
        ("difficulty", "INTEGER DEFAULT 1"),
        ("handshape", "TEXT"),
        ("location", "TEXT"),
        ("movement", "TEXT"),
        ("expression", "TEXT"),
        ("usage_example", "TEXT"),
    ]
    for col_name, col_type in label_columns:
        await _safe_add_column(db, "labels", col_name, col_type)

    # videos jadvaliga yangi ustunlar
    video_columns = [
        ("s3_url", "TEXT"),
        ("landmarks_url", "TEXT"),
        ("annotation_notes", "TEXT"),
    ]
    for col_name, col_type in video_columns:
        await _safe_add_column(db, "videos", col_name, col_type)

    # sign_variants jadvalini yaratish (agar mavjud bo'lmasa — SCHEMA da allaqachon bor)
    # Migratsiya uchun alohida so'rov kerak emas chunki CREATE TABLE IF NOT EXISTS


async def _safe_add_column(db, table: str, column: str, col_type: str):
    """ALTER TABLE ... ADD COLUMN — agar ustun allaqachon bo'lsa xatolik bermaydi."""
    try:
        if db.is_postgres:
            await db.conn.execute(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}"
            )
        else:
            await db.conn.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
            )
    except Exception:
        pass  # Ustun allaqachon mavjud


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


async def add_label(
    word_uz: str,
    word_ru: Optional[str] = None,
    category: Optional[str] = None,
    target_count: int = 50
):
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
                      v.s3_url, v.landmarks_url,
                      l.word_uz, l.word_ru, l.category
               FROM videos v
               JOIN labels l ON v.label_id = l.label_id
               WHERE v.status = 'approved'
               ORDER BY l.word_uz, v.video_id"""
        )
        return await cursor.fetchall()
    finally:
        await db.close()


async def get_video_by_id(video_id: int):
    db = await _connect()
    try:
        cursor = await db.execute(
            """SELECT v.*, l.word_uz, l.word_ru, l.category
               FROM videos v
               JOIN labels l ON v.label_id = l.label_id
               WHERE v.video_id = ?""",
            (video_id,),
        )
        return await cursor.fetchone()
    finally:
        await db.close()


async def update_video_s3_url(video_id: int, s3_url: str):
    db = await _connect()
    try:
        await db.execute(
            "UPDATE videos SET s3_url = ? WHERE video_id = ?",
            (s3_url, video_id),
        )
        await db.commit()
    finally:
        await db.close()


async def update_video_landmarks_url(video_id: int, landmarks_url: str):
    db = await _connect()
    try:
        await db.execute(
            "UPDATE videos SET landmarks_url = ? WHERE video_id = ?",
            (landmarks_url, video_id),
        )
        await db.commit()
    finally:
        await db.close()


async def add_sign_variant(label_id: int, region: str, video_file_id: str, notes: Optional[str] = None):
    db = await _connect()
    try:
        await db.execute(
            "INSERT INTO sign_variants (label_id, region, video_file_id, notes) VALUES (?, ?, ?, ?)",
            (label_id, region, video_file_id, notes),
        )
        await db.commit()
    finally:
        await db.close()


async def get_sign_variants(label_id: int):
    db = await _connect()
    try:
        cursor = await db.execute(
            "SELECT * FROM sign_variants WHERE label_id = ?",
            (label_id,),
        )
        return await cursor.fetchall()
    finally:
        await db.close()


async def update_label_annotation(
    label_id: int,
    handshape: Optional[str] = None,
    location: Optional[str] = None,
    movement: Optional[str] = None,
    expression: Optional[str] = None,
    usage_example: Optional[str] = None
):
    db = await _connect()
    try:
        await db.execute(
            """UPDATE labels
               SET handshape = ?, location = ?, movement = ?, expression = ?, usage_example = ?
               WHERE label_id = ?""",
            (handshape, location, movement, expression, usage_example, label_id),
        )
        await db.commit()
    finally:
        await db.close()

