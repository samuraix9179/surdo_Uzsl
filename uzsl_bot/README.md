# UZSL Dataset Bot

Telegram bot orqali O'zbek imo-ishora tili (UZSL) videolarini yig'ish, tasniflash, moderatsiya qilish va eksport qilish uchun to'liq ishchi tizim.

> Eslatma: bu loyiha `surdo/uzsl_translator` (Flutter ilovasi) dan alohida, mustaqil Python loyihasi.

## Imkoniyatlar

**Foydalanuvchi uchun:**
- 3 bosqichli ro'yxatdan o'tish (yosh, UZSL darajasi, kar/soqovligi)
- Inline tugmali asosiy menyu
- Video yuborish + avtomatik validatsiya (davomiylik, hajm)
- "Bu belgini bilmayman" — keyingi belgiga o'tish
- Profil, statistika, mukofotlar (badge), reyting (leaderboard)
- 50/100/250 video uchun PDF sertifikat (Unicode shrift — o'zbek/kirill harflari to'g'ri chiqadi)
- `/delete_my_data` — GDPR bo'yicha ma'lumotlarni o'chirish

**Admin uchun:**
- `/admin` — inline panel
- `/moderate` — tasdiqlash / rad etish (sabab tanlash bilan), foydalanuvchiga avtomatik bildirishnoma
- `/stats` — umumiy statistika, belgilar taqsimoti, sifatsiz video foizi
- `/addlabel` — yangi belgi qo'shish
- `/upload_example <label_id>` — belgi uchun namuna video yuklash
- `/broadcast` — barcha foydalanuvchilarga e'lon
- `/export` — tasdiqlangan videolar metadata'sini JSON ko'rinishida olish

**Texnik:**
- python-telegram-bot v21 (post_init, rate limiter)
- `PicklePersistence` — qayta ishga tushganda suhbat holati saqlanadi
- SQLite (WAL rejimi, foreign keys, indekslar)
- Global error handler, anti-spam cooldown
- `setMyCommands` — Telegram menyusi avtomatik to'ldiriladi

## Talablar

- Python 3.10+
- Telegram bot tokeni (@BotFather orqali)

## O'rnatish

```bash
cd uzsl_bot

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

pip install -r requirements.txt

copy .env.example .env       # Windows
# cp .env.example .env       # Linux/Mac
```

`.env` faylini tahrirlang:

```
BOT_TOKEN=8123456789:AAH...your_token_here
ADMIN_IDS=123456789,987654321
```

> Telegram user_id ni topish uchun @userinfobot ga yozing.

## Ishga tushirish

```bash
python main.py
```

`🤖 UZSL Dataset Bot ishga tushdi...` — tayyor. Telegram'da botni oching va `/start` yuboring.
`data/bot.db` va `data/bot_persistence.pkl` avtomatik yaratiladi.

## Komandalar

| Komanda | Kim uchun | Tavsif |
| :--- | :--- | :--- |
| `/start` | hamma | Ro'yxatdan o'tish / menyu |
| `/submit` | hamma | Video yuborish |
| `/labels` | hamma | Belgilar ro'yxati |
| `/profile` | hamma | Profil va statistika |
| `/leaderboard` | hamma | Top hissa qo'shuvchilar |
| `/help` | hamma | Yordam |
| `/delete_my_data` | hamma | Ma'lumotlarni o'chirish |
| `/admin` | admin | Admin panel |
| `/moderate` | admin | Videolarni moderatsiya |
| `/stats` | admin | Statistika |
| `/addlabel` | admin | Yangi belgi qo'shish |
| `/upload_example` | admin | Belgi uchun namuna video yuklash |
| `/broadcast` | admin | E'lon yuborish |
| `/export` | admin | Metadata JSON eksport |

## Videolarni yuklab olish (lokal)

```bash
python -m utils.export
```

Natija: `exports/salom/`, `exports/rahmat/`, ... papkalari + `exports/metadata.json`.

## Loyiha tuzilishi

```
uzsl_bot/
├── main.py              # Ishga tushirish, handlerlarni ulash, error handler
├── config.py            # Sozlamalar
├── database.py          # SQLite (async)
├── keyboards.py         # Inline klaviaturalar
├── handlers/
│   ├── start.py         # Ro'yxatdan o'tish, delete_my_data
│   ├── submit_video.py  # Video yuborish oqimi
│   ├── profile.py       # Profil, labels, leaderboard, help, menyu
│   └── admin.py         # Moderatsiya, stats, addlabel, broadcast, export
├── utils/
│   ├── rewards.py       # Badge + PDF sertifikat
│   └── export.py        # Videolarni yuklab olish
├── data/                # bot.db, persistence (avtomatik)
└── requirements.txt
```

## Deploy

VPS'da systemd service (Ubuntu):

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
```

Batafsil texnik vazifa: `../telegram_bot_tz.md`
