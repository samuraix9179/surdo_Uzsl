import os

from dotenv import load_dotenv

load_dotenv()

# --- Asosiy sozlamalar ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# Yo'llar
DATA_DIR = "data"
DB_PATH = os.path.join(DATA_DIR, "bot.db")
EXPORT_DIR = "exports"
PERSISTENCE_PATH = os.path.join(DATA_DIR, "bot_persistence.pkl")

# --- Video cheklovlari ---
MIN_VIDEO_DURATION = 1.0      # soniya
MAX_VIDEO_DURATION = 10.0     # soniya
MAX_FILE_SIZE_MB = 50

# --- Anti-spam ---
# Bir foydalanuvchi necha soniyada bir marta video yubora oladi
VIDEO_COOLDOWN_SECONDS = 2

# --- Mukofotlar (badge'lar) ---
# threshold: (emoji, nom, sertifikat_kerakmi)
BADGES = {
    10: ("🥉", "Faol ko'ngilli", False),
    50: ("🥈", "Senior contributor", True),
    100: ("🥇", "UZSL qahramoni", True),
    250: ("💎", "Legendary contributor", True),
}

# --- Moderatsiya rad etish sabablari ---
REJECTION_REASONS = {
    "dark": "Yorug'lik yetarli emas",
    "blurry": "Video xira / tebrangan",
    "wrong": "Noto'g'ri belgi ko'rsatilgan",
    "incomplete": "Qo'l/yelka to'liq ko'rinmayapti",
    "duplicate": "Takroriy video",
    "other": "Boshqa sabab",
}

# --- Yosh guruhlari va UZSL darajalari ---
AGE_GROUPS = ["<18", "18-30", "30-50", "50+"]

UZSL_LEVEL_MAP = {
    "Boshlang'ich": "beginner",
    "O'rta": "intermediate",
    "Mutaxassis (ona tili)": "native",
}
UZSL_LEVEL_LABELS = {
    "beginner": "Boshlang'ich",
    "intermediate": "O'rta",
    "native": "Mutaxassis (ona tili)",
}
