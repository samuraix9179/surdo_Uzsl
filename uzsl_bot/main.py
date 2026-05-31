import logging
import os

from telegram import BotCommand, Update
from telegram.ext import Application, PicklePersistence, ContextTypes

from config import BOT_TOKEN, DATA_DIR, PERSISTENCE_PATH, ADMIN_IDS
from database import init_db

# Handlerlar
from handlers.start import (
    registration_handler, delete_data_handler, delete_callback_handler,
)
from handlers.submit_video import submit_handler
from handlers.profile import (
    profile_handler, leaderboard_handler, labels_handler,
    help_handler, menu_callback_handler,
)
from handlers.admin import (
    admin_panel_handler, stats_handler, moderate_handler, export_handler,
    moderation_action_handler, rejection_handler, admin_menu_handler,
    addlabel_conv, broadcast_conv, upload_example_conv,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def _post_init(application: Application) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    await init_db()

    # Telegram menyusidagi komandalar ro'yxati
    await application.bot.set_my_commands([
        BotCommand("start", "Boshlash / asosiy menyu"),
        BotCommand("submit", "Video yuborish"),
        BotCommand("labels", "Belgilar ro'yxati"),
        BotCommand("profile", "Mening profilim"),
        BotCommand("leaderboard", "Top hissa qo'shuvchilar"),
        BotCommand("help", "Yordam"),
        BotCommand("delete_my_data", "Ma'lumotlarimni o'chirish"),
    ])
    logger.info("Bot tayyor. Adminlar: %s", ADMIN_IDS or "belgilanmagan")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Xatolik yuz berdi:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Kutilmagan xatolik yuz berdi. Birozdan keyin urinib ko'ring."
            )
        except Exception:
            pass


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN topilmadi. .env faylida BOT_TOKEN ni belgilang "
            "(.env.example dan nusxa oling)."
        )

    os.makedirs(DATA_DIR, exist_ok=True)
    persistence = PicklePersistence(filepath=PERSISTENCE_PATH)

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .persistence(persistence)
        .post_init(_post_init)
        .build()
    )

    # --- Conversation handlerlar (birinchi bo'lib) ---
    app.add_handler(registration_handler)
    app.add_handler(submit_handler)
    app.add_handler(addlabel_conv)
    app.add_handler(broadcast_conv)
    app.add_handler(upload_example_conv)

    # --- Foydalanuvchi komandalari ---
    app.add_handler(profile_handler)
    app.add_handler(leaderboard_handler)
    app.add_handler(labels_handler)
    app.add_handler(help_handler)
    app.add_handler(delete_data_handler)

    # --- Admin komandalari ---
    app.add_handler(admin_panel_handler)
    app.add_handler(stats_handler)
    app.add_handler(moderate_handler)
    app.add_handler(export_handler)

    # --- Callback query handlerlar ---
    app.add_handler(menu_callback_handler)
    app.add_handler(delete_callback_handler)
    app.add_handler(moderation_action_handler)
    app.add_handler(rejection_handler)
    app.add_handler(admin_menu_handler)

    # --- Xatolarni ushlash ---
    app.add_error_handler(error_handler)

    print("🤖 UZSL Dataset Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
