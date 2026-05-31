# UZSL DATASET BOT — TELEGRAM (TZ + Kod)

**Maqsad:** Telegram bot orqali UZSL videolarini yig'ish, tasniflash va saqlash
**Vaqt:** 1 hafta ichida ishchi versiya
**Til:** Python 3.10+
**Asosiy kutubxona:** python-telegram-bot (v21+)

---

## 1. NIMA UCHUN BU MUHIM

Loyihaning eng katta to'sig'i — UZSL dataset yo'qligi. Mobil ilova kutmasdan, bugundan boshlab ma'lumot yig'ishni boshlash kerak. Telegram bot — eng tezkor yo'l, chunki:

- Karlar jamiyati a'zolarining 90%+ Telegram'dan foydalanadi
- Ilova yuklab olish, ro'yxatdan o'tish kerak emas — link bosib, video yuborish
- Sifatli video kompressiya (Telegram avtomatik)
- Bepul cloud storage (video Telegram serverida saqlanadi)
- Boshqarish oson — admin panel sifatida ishlaydi

---

## 2. BOT IMKONIYATLARI

### 2.1 Foydalanuvchi uchun (oddiy ko'ngillilar)

**🎬 Video yuborish:**
- Belgilar ro'yxatidan birini tanlash (masalan: "salom")
- Telefon kamerasidan video yozib yuborish (yoki galereyadan)
- Bot avtomatik tekshiradi: davomiyligi, sifati, format

**📚 Belgilar ro'yxati:**
- Ko'rish kerak bo'lgan belgilar (kim hali yuborilmaganlari)
- Misol video (agar mavjud bo'lsa) — qanday ko'rsatish kerak
- "Bu belgini bilmayman" — keyingi belgiga o'tish

**👤 Profil:**
- Ism, yosh guruhi, UZSL bilish darajasi
- Yuborilgan video soni
- Reyting (gamification — top-10 hissa qo'shuvchilar)

**🏆 Mukofotlar:**
- 10 ta video = "Faol ko'ngilli" badge
- 50 ta video = "Senior contributor" + sertifikat (PDF)
- 100 ta video = Kichik pul mukofoti (50,000 so'm) yoki sovg'a

### 2.2 Admin uchun (loyiha jamoasi)

**📊 Statistika:**
- Jami video soni
- Belgilar bo'yicha taqsimot (qaysi yetarli, qaysi kam)
- Faol foydalanuvchilar
- Sifatsiz video foizi

**✅ Moderatsiya:**
- Yangi videolarni ko'rib chiqish
- Tasdiqlash / rad etish
- Belgi yorlig'ini o'zgartirish (agar foydalanuvchi noto'g'ri tanlagan bo'lsa)

**📦 Eksport:**
- Tasdiqlangan videolarni ZIP qilib yuklab olish
- Metadata JSON (foydalanuvchi, belgi, sana, davomiyligi)
- Belgi/foydalanuvchi bo'yicha filtrlash

**🔧 Sozlamalar:**
- Yangi belgi qo'shish
- Mukofot tizimini sozlash
- E'lonlar yuborish (broadcast)

---

## 3. ARXITEKTURA

```
┌─────────────────────────────────────────────┐
│         TELEGRAM BOT (Python)               │
├─────────────────────────────────────────────┤
│  python-telegram-bot v21+                   │
│  ├── Handlers (komandalar, message, video)  │
│  ├── ConversationHandler (suhbat oqimi)     │
│  └── CallbackQueryHandler (tugmalar)        │
├─────────────────────────────────────────────┤
│  Business Logic                             │
│  ├── User manager                           │
│  ├── Video processor (validation)           │
│  ├── Label manager                          │
│  └── Reward system                          │
├─────────────────────────────────────────────┤
│  Database (SQLite → PostgreSQL kelajakda)   │
│  ├── users                                  │
│  ├── videos                                 │
│  ├── labels                                 │
│  └── moderation_queue                       │
├─────────────────────────────────────────────┤
│  Storage                                    │
│  ├── Video fayllari: Telegram file_id       │
│  ├── Lokal cache: /videos/                  │
│  └── Backup: Yandex.Disk / Google Drive     │
└─────────────────────────────────────────────┘
```

---

## 4. MA'LUMOTLAR BAZASI SXEMASI

```sql
-- Foydalanuvchilar
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,           -- Telegram user_id
    username TEXT,
    full_name TEXT,
    age_group TEXT,                        -- "<18", "18-30", "30-50", "50+"
    uzsl_level TEXT,                       -- "beginner", "intermediate", "native"
    is_deaf BOOLEAN DEFAULT 0,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    videos_submitted INTEGER DEFAULT 0,
    videos_approved INTEGER DEFAULT 0,
    is_admin BOOLEAN DEFAULT 0
);

-- Belgilar (so'zlar)
CREATE TABLE labels (
    label_id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_uz TEXT NOT NULL UNIQUE,          -- "salom"
    word_ru TEXT,                          -- "привет"
    category TEXT,                         -- "salomlashish", "raqam", "savol"
    example_video_id TEXT,                 -- Telegram file_id
    target_count INTEGER DEFAULT 50,       -- Kerakli video soni
    current_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1
);

-- Videolar
CREATE TABLE videos (
    video_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    label_id INTEGER NOT NULL,
    telegram_file_id TEXT NOT NULL,
    duration_seconds REAL,
    file_size_bytes INTEGER,
    width INTEGER,
    height INTEGER,
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',         -- pending, approved, rejected
    moderator_id INTEGER,
    moderated_at DATETIME,
    rejection_reason TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (label_id) REFERENCES labels(label_id)
);

-- Mukofotlar (achievements)
CREATE TABLE achievements (
    achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    badge_name TEXT NOT NULL,
    earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

---

## 5. ASOSIY KOD

### 5.1 Loyiha tuzilishi

```
uzsl_bot/
├── main.py                  # Botni ishga tushirish
├── config.py                # Sozlamalar (token, admin id)
├── database.py              # SQLite bilan ishlash
├── handlers/
│   ├── __init__.py
│   ├── start.py             # /start, ro'yxatdan o'tish
│   ├── submit_video.py      # Video yuborish oqimi
│   ├── profile.py           # Profil va statistika
│   ├── admin.py             # Admin komandalari
│   └── moderation.py        # Video moderatsiyasi
├── utils/
│   ├── __init__.py
│   ├── validators.py        # Video tekshirish
│   └── rewards.py           # Mukofot tizimi
├── data/
│   └── bot.db               # SQLite database
└── requirements.txt
```

### 5.2 requirements.txt

```
python-telegram-bot==21.6
python-dotenv==1.0.1
aiosqlite==0.20.0
```

### 5.3 config.py

```python
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
DB_PATH = "data/bot.db"

# Video cheklovlari
MIN_VIDEO_DURATION = 1.0      # soniya
MAX_VIDEO_DURATION = 10.0
MAX_FILE_SIZE_MB = 50

# Mukofotlar
BADGES = {
    10: ("🥉", "Faol ko'ngilli"),
    50: ("🥈", "Senior contributor"),
    100: ("🥇", "UZSL qahramoni"),
    250: ("💎", "Legendary contributor"),
}
```

### 5.4 .env (yashirin fayl, git'ga qo'shilmaydi)

```
BOT_TOKEN=8123456789:AAH...your_token_here
ADMIN_IDS=123456789,987654321
```

### 5.5 database.py

```python
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
    is_admin BOOLEAN DEFAULT 0
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


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)

        # Belgilar mavjud emasligini tekshirish
        cursor = await db.execute("SELECT COUNT(*) FROM labels")
        count = (await cursor.fetchone())[0]

        if count == 0:
            await db.executemany(
                "INSERT INTO labels (word_uz, word_ru, category) VALUES (?, ?, ?)",
                INITIAL_LABELS,
            )
        await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()


async def create_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name),
        )
        await db.commit()


async def update_user_profile(user_id: int, age_group: str, uzsl_level: str, is_deaf: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET age_group = ?, uzsl_level = ?, is_deaf = ? WHERE user_id = ?",
            (age_group, uzsl_level, is_deaf, user_id),
        )
        await db.commit()


async def get_labels_needing_videos(limit: int = 10):
    """Eng kam video bor belgilarni qaytaradi."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM labels
               WHERE is_active = 1 AND current_count < target_count
               ORDER BY current_count ASC
               LIMIT ?""",
            (limit,),
        )
        return await cursor.fetchall()


async def get_label_by_id(label_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM labels WHERE label_id = ?", (label_id,))
        return await cursor.fetchone()


async def save_video(user_id: int, label_id: int, file_id: str,
                     duration: float, file_size: int, width: int, height: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO videos
               (user_id, label_id, telegram_file_id, duration_seconds,
                file_size_bytes, width, height)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, label_id, file_id, duration, file_size, width, height),
        )
        # Foydalanuvchi va belgi hisoblagichlarini yangilash
        await db.execute(
            "UPDATE users SET videos_submitted = videos_submitted + 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.execute(
            "UPDATE labels SET current_count = current_count + 1 WHERE label_id = ?",
            (label_id,),
        )
        await db.commit()


async def get_user_stats(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT COUNT(*) as total,
                      SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                      SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
               FROM videos WHERE user_id = ?""",
            (user_id,),
        )
        return await cursor.fetchone()


async def get_leaderboard(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT full_name, videos_submitted, videos_approved
               FROM users
               WHERE videos_submitted > 0
               ORDER BY videos_approved DESC, videos_submitted DESC
               LIMIT ?""",
            (limit,),
        )
        return await cursor.fetchall()


async def get_pending_videos(limit: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
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


async def moderate_video(video_id: int, status: str, moderator_id: int, reason: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
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
                    (row[0],),
                )
        await db.commit()
```

### 5.6 handlers/start.py

```python
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from database import get_user, create_user, update_user_profile

AGE, UZSL_LEVEL, IS_DEAF = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = await get_user(user.id)

    if db_user and db_user["age_group"]:
        # Allaqachon ro'yxatdan o'tgan
        await update.message.reply_text(
            f"Xush kelibsiz, {user.first_name}! 👋\n\n"
            "Asosiy menyu:\n"
            "/submit — Video yuborish\n"
            "/labels — Belgilar ro'yxati\n"
            "/profile — Mening profilim\n"
            "/leaderboard — Top hissa qo'shuvchilar\n"
            "/help — Yordam"
        )
        return ConversationHandler.END

    # Yangi foydalanuvchi
    await create_user(user.id, user.username or "", user.full_name)

    await update.message.reply_text(
        f"Assalomu alaykum, {user.first_name}! 🤝\n\n"
        "Bu bot O'zbek imo-ishora tili (UZSL) uchun dataset yig'adi.\n"
        "Sizning videolaringiz kar va soqovlar uchun tarjima ilovasini yaratishga yordam beradi.\n\n"
        "Boshlash uchun bir nechta savolga javob bering.\n\n"
        "**1/3:** Yoshingiz qaysi guruhda?",
        reply_markup=ReplyKeyboardMarkup(
            [["<18", "18-30"], ["30-50", "50+"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
        parse_mode="Markdown",
    )
    return AGE


async def ask_uzsl_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["age_group"] = update.message.text
    await update.message.reply_text(
        "**2/3:** UZSL bilish darajangiz?",
        reply_markup=ReplyKeyboardMarkup(
            [["Boshlang'ich"], ["O'rta"], ["Mutaxassis (ona tili)"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
        parse_mode="Markdown",
    )
    return UZSL_LEVEL


async def ask_is_deaf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    level_map = {
        "Boshlang'ich": "beginner",
        "O'rta": "intermediate",
        "Mutaxassis (ona tili)": "native",
    }
    context.user_data["uzsl_level"] = level_map.get(update.message.text, "beginner")

    await update.message.reply_text(
        "**3/3:** Siz kar yoki soqovmisiz?",
        reply_markup=ReplyKeyboardMarkup(
            [["Ha"], ["Yo'q"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
        parse_mode="Markdown",
    )
    return IS_DEAF


async def finish_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_deaf = update.message.text == "Ha"
    user_id = update.effective_user.id

    await update_user_profile(
        user_id,
        context.user_data["age_group"],
        context.user_data["uzsl_level"],
        is_deaf,
    )

    await update.message.reply_text(
        "✅ Ro'yxatdan o'tdingiz! Rahmat.\n\n"
        "Endi /submit komandasi orqali video yuborishni boshlang.\n"
        "Har bir video bizga juda muhim 🙏"
    )
    return ConversationHandler.END


registration_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        AGE: [MessageHandler(filters.Regex("^(<18|18-30|30-50|50\\+)$"), ask_uzsl_level)],
        UZSL_LEVEL: [MessageHandler(filters.Regex("^(Boshlang'ich|O'rta|Mutaxassis.*)$"), ask_is_deaf)],
        IS_DEAF: [MessageHandler(filters.Regex("^(Ha|Yo'q)$"), finish_registration)],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)
```

### 5.7 handlers/submit_video.py

```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)

from database import (
    get_labels_needing_videos, get_label_by_id,
    save_video, get_user
)
from config import MIN_VIDEO_DURATION, MAX_VIDEO_DURATION, MAX_FILE_SIZE_MB
from utils.rewards import check_and_award_badge

CHOOSE_LABEL, WAITING_VIDEO = range(10, 12)


async def submit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user or not user["age_group"]:
        await update.message.reply_text("Avval /start orqali ro'yxatdan o'ting.")
        return ConversationHandler.END

    labels = await get_labels_needing_videos(limit=8)
    if not labels:
        await update.message.reply_text("Hozircha barcha belgilar uchun yetarli video yig'ilgan. Rahmat! 🎉")
        return ConversationHandler.END

    # Inline tugmalar
    buttons = []
    for label in labels:
        progress = f"{label['current_count']}/{label['target_count']}"
        buttons.append([InlineKeyboardButton(
            f"{label['word_uz']}  ({progress})",
            callback_data=f"label_{label['label_id']}"
        )])

    await update.message.reply_text(
        "Qaysi belgini ko'rsatmoqchisiz?\n"
        "_Ro'yxatdagi belgilar eng kam videoga ega bo'lganlar._",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
    )
    return CHOOSE_LABEL


async def label_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    label_id = int(query.data.split("_")[1])
    label = await get_label_by_id(label_id)
    context.user_data["current_label_id"] = label_id
    context.user_data["current_label_word"] = label["word_uz"]

    instructions = (
        f"📹 Belgi: **{label['word_uz']}**\n\n"
        "**Video yozish bo'yicha qoidalar:**\n"
        "• Davomiyligi: 1-10 soniya\n"
        "• Yorug' joyda turing\n"
        "• Yelka va qo'llaringiz to'liq ko'rinishi kerak\n"
        "• Bitta belgini bir marta sekin va aniq ko'rsating\n"
        "• Kamera mustahkam turishi kerak (tebranmasin)\n\n"
        "Videoni yozib, shu yerga yuboring 👇\n\n"
        "/cancel — bekor qilish"
    )

    if label["example_video_id"]:
        await query.message.reply_video(
            label["example_video_id"],
            caption=instructions,
            parse_mode="Markdown",
        )
    else:
        await query.message.reply_text(instructions, parse_mode="Markdown")

    return WAITING_VIDEO


async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.video_note

    if not video:
        await update.message.reply_text("Iltimos, video yuboring (matn yoki rasm emas).")
        return WAITING_VIDEO

    # Tekshirishlar
    if video.duration < MIN_VIDEO_DURATION:
        await update.message.reply_text(
            f"❌ Video juda qisqa ({video.duration}s).\n"
            f"Minimum {MIN_VIDEO_DURATION}s bo'lishi kerak. Qaytadan yozing."
        )
        return WAITING_VIDEO

    if video.duration > MAX_VIDEO_DURATION:
        await update.message.reply_text(
            f"❌ Video juda uzun ({video.duration}s).\n"
            f"Maximum {MAX_VIDEO_DURATION}s bo'lishi kerak. Faqat bitta belgini yozing."
        )
        return WAITING_VIDEO

    file_size_mb = video.file_size / (1024 * 1024) if video.file_size else 0
    if file_size_mb > MAX_FILE_SIZE_MB:
        await update.message.reply_text(
            f"❌ Fayl juda katta ({file_size_mb:.1f} MB). Maximum {MAX_FILE_SIZE_MB} MB."
        )
        return WAITING_VIDEO

    # Saqlash
    user_id = update.effective_user.id
    label_id = context.user_data["current_label_id"]
    label_word = context.user_data["current_label_word"]

    await save_video(
        user_id=user_id,
        label_id=label_id,
        file_id=video.file_id,
        duration=video.duration,
        file_size=video.file_size or 0,
        width=getattr(video, "width", 0),
        height=getattr(video, "height", 0),
    )

    await update.message.reply_text(
        f"✅ Rahmat! Sizning '**{label_word}**' videongiz qabul qilindi.\n"
        f"Tez orada moderator tekshirib chiqadi.\n\n"
        "Yana yuborish: /submit\n"
        "Profilim: /profile",
        parse_mode="Markdown",
    )

    # Mukofot tekshirish
    badge = await check_and_award_badge(user_id)
    if badge:
        await update.message.reply_text(
            f"🎉 Yangi yutuq: {badge['emoji']} **{badge['name']}**!\n"
            f"Siz {badge['threshold']} ta videoga yetdingiz!",
            parse_mode="Markdown",
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi.")
    return ConversationHandler.END


submit_handler = ConversationHandler(
    entry_points=[CommandHandler("submit", submit_start)],
    states={
        CHOOSE_LABEL: [CallbackQueryHandler(label_chosen, pattern="^label_")],
        WAITING_VIDEO: [
            MessageHandler(filters.VIDEO | filters.VIDEO_NOTE, receive_video),
            CommandHandler("cancel", cancel),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
```

### 5.8 handlers/profile.py

```python
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database import get_user, get_user_stats, get_leaderboard
from config import BADGES


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    stats = await get_user_stats(user_id)

    if not user:
        await update.message.reply_text("Avval /start orqali ro'yxatdan o'ting.")
        return

    # Yutuqlar
    earned_badges = [f"{e} {n}" for t, (e, n) in BADGES.items() if user["videos_approved"] >= t]
    badges_text = "\n".join(earned_badges) if earned_badges else "_Hali yo'q_"

    # Keyingi maqsad
    next_badge = next(((t, e, n) for t, (e, n) in BADGES.items() if user["videos_approved"] < t), None)
    next_goal = f"\n🎯 Keyingi: {next_badge[1]} {next_badge[2]} ({next_badge[0]} ta video)" if next_badge else ""

    text = (
        f"👤 **Sizning profilingiz**\n\n"
        f"Ism: {user['full_name']}\n"
        f"UZSL: {user['uzsl_level']}\n"
        f"Yosh: {user['age_group']}\n\n"
        f"📊 **Statistika:**\n"
        f"Jami yuborilgan: {stats['total'] or 0}\n"
        f"✅ Tasdiqlangan: {stats['approved'] or 0}\n"
        f"⏳ Ko'rib chiqilmoqda: {stats['pending'] or 0}\n\n"
        f"🏆 **Yutuqlar:**\n{badges_text}{next_goal}"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = await get_leaderboard(10)
    if not top:
        await update.message.reply_text("Hozircha hech kim video yubormagan.")
        return

    medals = ["🥇", "🥈", "🥉"] + ["▫️"] * 7
    lines = ["🏆 **Top 10 hissa qo'shuvchilar**\n"]
    for i, user in enumerate(top):
        lines.append(
            f"{medals[i]} {user['full_name']} — "
            f"{user['videos_approved']} tasdiqlangan ({user['videos_submitted']} jami)"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


profile_handler = CommandHandler("profile", profile)
leaderboard_handler = CommandHandler("leaderboard", leaderboard)
```

### 5.9 handlers/admin.py

```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from database import get_pending_videos, moderate_video
from config import ADMIN_IDS


def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("⛔ Bu komanda faqat adminlar uchun.")
            return
        return await func(update, context)
    return wrapper


@admin_only
async def moderate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Navbatdagi tasdiqlanmagan videoni ko'rsatadi."""
    videos = await get_pending_videos(limit=1)
    if not videos:
        await update.message.reply_text("✅ Barcha videolar moderatsiyadan o'tgan!")
        return

    video = videos[0]
    buttons = [
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{video['video_id']}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{video['video_id']}"),
        ]
    ]

    await update.message.reply_video(
        video["telegram_file_id"],
        caption=(
            f"📹 **Belgi:** {video['word_uz']}\n"
            f"👤 **Foydalanuvchi:** {video['user_name']}\n"
            f"⏱ **Davomiyligi:** {video['duration_seconds']}s\n"
            f"📅 **Yuborilgan:** {video['submitted_at']}"
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
    )


async def handle_moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        await query.answer("⛔ Sizda ruxsat yo'q", show_alert=True)
        return

    action, video_id = query.data.split("_")
    video_id = int(video_id)

    if action == "approve":
        await moderate_video(video_id, "approved", query.from_user.id)
        await query.edit_message_caption(caption=query.message.caption + "\n\n✅ **TASDIQLANDI**", parse_mode="Markdown")
    elif action == "reject":
        await moderate_video(video_id, "rejected", query.from_user.id, "Sifati past")
        await query.edit_message_caption(caption=query.message.caption + "\n\n❌ **RAD ETILDI**", parse_mode="Markdown")

    # Avtomatik keyingi videoga o'tish
    await moderate(update, context)


moderate_handler = CommandHandler("moderate", moderate)
moderation_callback = CallbackQueryHandler(handle_moderation, pattern="^(approve|reject)_")
```

### 5.10 utils/rewards.py

```python
from config import BADGES
from database import get_user_stats
import aiosqlite
from config import DB_PATH


async def check_and_award_badge(user_id: int):
    """Yangi badge olganmi tekshiradi."""
    stats = await get_user_stats(user_id)
    approved = stats["approved"] or 0

    # Hozirgacha olingan badge'lar
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT badge_name FROM achievements WHERE user_id = ?", (user_id,)
        )
        existing = {row[0] for row in await cursor.fetchall()}

    # Yangi badge bormi?
    for threshold, (emoji, name) in BADGES.items():
        if approved >= threshold and name not in existing:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT INTO achievements (user_id, badge_name) VALUES (?, ?)",
                    (user_id, name),
                )
                await db.commit()
            return {"emoji": emoji, "name": name, "threshold": threshold}

    return None
```

### 5.11 main.py

```python
import asyncio
import logging

from telegram.ext import Application

from config import BOT_TOKEN
from database import init_db
from handlers.start import registration_handler
from handlers.submit_video import submit_handler
from handlers.profile import profile_handler, leaderboard_handler
from handlers.admin import moderate_handler, moderation_callback

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def main():
    # Database tayyorlash
    asyncio.get_event_loop().run_until_complete(init_db())

    # Bot
    app = Application.builder().token(BOT_TOKEN).build()

    # Handler'larni ulash
    app.add_handler(registration_handler)
    app.add_handler(submit_handler)
    app.add_handler(profile_handler)
    app.add_handler(leaderboard_handler)
    app.add_handler(moderate_handler)
    app.add_handler(moderation_callback)

    print("🤖 UZSL Dataset Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
```

---

## 6. ISHGA TUSHIRISH

### 6.1 Bot yaratish (Telegram)

1. Telegram'da @BotFather ga yozing
2. `/newbot` komandasini yuboring
3. Bot nomini kiriting: UZSL Dataset Bot
4. Username kiriting: uzsl_dataset_bot (band bo'lsa boshqa nom)
5. Bot tokenni nusxalang (`8123456:AAH...`)

### 6.2 Loyihani sozlash

```bash
# Loyiha papkasini yaratish
mkdir uzsl_bot && cd uzsl_bot

# Virtual environment
python3 -m venv venv
source venv/bin/activate    # Linux/Mac
# venv\Scripts\activate     # Windows

# Yuqoridagi 5.2 ga ko'ra requirements.txt yarating
pip install -r requirements.txt

# .env fayl yarating va token'ni qo'shing
echo "BOT_TOKEN=YOUR_TOKEN_HERE" > .env
echo "ADMIN_IDS=YOUR_TELEGRAM_USER_ID" >> .env

# Papkalarni yarating
mkdir -p handlers utils data
touch handlers/__init__.py utils/__init__.py

# Yuqoridagi barcha .py fayllarni tegishli joylarga joylashtiring
```

> **Telegram user_id ni qanday topish:** @userinfobot ga yozing — sizning ID raqamingizni qaytaradi.

### 6.3 Ishga tushirish

```bash
python main.py
```

Hammasi to'g'ri bo'lsa: `🤖 UZSL Dataset Bot ishga tushdi...`
Endi Telegram'da botni oching va `/start` yuboring.

---

## 7. SERVERGA QO'YISH (DEPLOY)

Lokalda doimo ishlashi noqulay. Server'ga qo'yish variantlari:

### 7.1 VPS (eng yaxshi nazorat) — ~$5/oy

- Hetzner, Hostinger, DigitalOcean
- Ubuntu 22.04, 1 CPU, 1 GB RAM yetarli
- systemd service sifatida ishga tushirish

```ini
# /etc/systemd/system/uzsl-bot.service
[Unit]
Description=UZSL Dataset Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/uzsl_bot
ExecStart=/home/ubuntu/uzsl_bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable uzsl-bot
sudo systemctl start uzsl-bot
sudo systemctl status uzsl-bot
```

### 7.2 Railway / Render (eng oson) — bepul yoki ~$5/oy

- GitHub'ga kod yuklang
- Railway/Render'da "Deploy from GitHub" tanlang
- Environment variables: `BOT_TOKEN`, `ADMIN_IDS`

### 7.3 Oracle Cloud Free Tier (mutlaqo bepul, doimiy)

- 1-2 ta VM bepul (Always Free)
- Ariza topshirish kerak, ammo arziydi

---

## 8. ANALITIKA VA EKSPORT

### 8.1 Videolarni yuklab olish skripti

`utils/export.py`:

```python
import asyncio
import aiosqlite
import aiohttp
import os
from config import DB_PATH, BOT_TOKEN

EXPORT_DIR = "exports"


async def download_all_approved():
    os.makedirs(EXPORT_DIR, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT v.*, l.word_uz
               FROM videos v
               JOIN labels l ON v.label_id = l.label_id
               WHERE v.status = 'approved'"""
        )
        videos = await cursor.fetchall()

    async with aiohttp.ClientSession() as session:
        for v in videos:
            # Telegram'dan file path olish
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={v['telegram_file_id']}"
            async with session.get(url) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    continue
                file_path = data["result"]["file_path"]

            # Faylni yuklab olish
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            label_dir = os.path.join(EXPORT_DIR, v["word_uz"])
            os.makedirs(label_dir, exist_ok=True)
            output_path = os.path.join(label_dir, f"{v['video_id']}_{v['user_id']}.mp4")

            async with session.get(file_url) as resp:
                with open(output_path, "wb") as f:
                    f.write(await resp.read())

            print(f"✅ Saved: {output_path}")


if __name__ == "__main__":
    asyncio.run(download_all_approved())
```

Ishga tushirish: `python -m utils.export`
Natijada `exports/salom/`, `exports/rahmat/`, ... papkalari paydo bo'ladi.

---

## 9. KENGAYTIRISH G'OYALARI (KEYINGI BOSQICHLAR)

- Misol videolarni admin yuklashi — `/upload_example label_id` komandasi
- Avtomatik sifat tekshirish — OpenCV bilan yorug'lik, qo'l ko'rinishi tahlili
- Web admin panel — Django yoki Flask + Bootstrap
- Push e'lon — admin barcha foydalanuvchilarga xabar yuborishi (broadcast)
- Foydalanuvchi guruhlari — kar foydalanuvchilar uchun alohida sifatli ma'lumotlar
- Mini-app (Telegram Web App) — bot ichida to'liq interfeys
- AI tekshirish — yuborilgan videoni MediaPipe orqali tahlil qilib, qo'l ko'rinmasa avtomatik rad etish

---

## 10. 1 HAFTALIK REJA

| Kun | Vazifa |
| :--- | :--- |
| 1 | BotFather'da bot yaratish, kodni klonlash, lokal ishga tushirish |
| 2 | /start va ro'yxatdan o'tishni test qilish, xato bo'lsa to'g'rilash |
| 3 | /submit orqali 5-10 ta test video yuborish, validatsiyalarni tekshirish |
| 4 | Admin moderatsiya panelini test qilish, 30 ta belgini ko'rib chiqish |
| 5 | VPS yoki Railway'ga deploy qilish, doimiy ishlashini ta'minlash |
| 6 | Karlar jamiyatiga bot havolasini yuborish, dastlabki 5-10 ko'ngillini topish |
| 7 | Birinchi 50-100 ta video kelishini kuzatish, eksport qilib tekshirish |

---

## 11. ESLATMA: MAXFIYLIK VA ROZILIK

Birinchi marta `/start` qilganda foydalanuvchiga aniq aytish kerak:

- Videolar UZSL tarjima ilovasini o'rgatish uchun ishlatiladi
- Hech qachon shaxsiy maqsadda tarqatilmaydi
- Foydalanuvchi istalgan vaqtda `/delete_my_data` orqali o'z ma'lumotlarini o'chirishi mumkin
- Yoshi 18 dan kichik bo'lsa, ota-onaning roziligi kerak

Bu — qonuniy va axloqiy talab. Ayniqsa O'zbekiston "Shaxsiy ma'lumotlar to'g'risida"gi qonuni va GDPR uchun.

---

*Tayyor. Savol bo'lsa yozing — birgalikda deploy qilamiz.*
