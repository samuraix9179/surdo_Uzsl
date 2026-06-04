from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)

from database import (
    get_user, create_user, update_user_profile, delete_user_data,
)
from config import UZSL_LEVEL_MAP
from keyboards import main_menu_kb, confirm_delete_kb

CONSENT, AGE, UZSL_LEVEL, IS_DEAF = range(4)

WELCOME_BACK = (
    "Xush kelibsiz, {name}! 👋\n\n"
    "Quyidagi menyudan foydalaning yoki komandalarni yozing:\n"
    "/submit — Video yuborish\n"
    "/labels — Belgilar ro'yxati\n"
    "/profile — Mening profilim\n"
    "/leaderboard — Top hissa qo'shuvchilar\n"
    "/help — Yordam"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = await get_user(user.id)

    if db_user and db_user["age_group"]:
        await update.message.reply_text(
            WELCOME_BACK.format(name=user.first_name),
            reply_markup=main_menu_kb(),
        )
        return ConversationHandler.END

    # GDPR Consent request screen
    consent_text = (
        f"Assalomu alaykum, {user.first_name}! 🤝\n\n"
        "Bu bot O'zbek imo-ishora tili (UZSL) uchun dataset yig'adi.\n"
        "Sizning videolaringiz kar va soqovlar uchun tarjima ilovasini yaratishga yordam beradi.\n\n"
        "🔒 *Maxfiylik va Ruxsatnomalar (GDPR):*\n"
        "1. Siz taqdim etgan shaxsiy ma'lumotlar va videolar faqatgina UZSL tarjimon modellarini "
        "o'rgatish uchun foydalaniladi.\n"
        "2. Ma'lumotlaringiz uchinchi shaxslarga berilmaydi va shaxsiy maqsadlarda foydalanilmaydi.\n"
        "3. Istalgan vaqtda /delete_my_data buyrug'i orqali profilingiz va barcha videolaringizni "
        "butunlay o'chirib tashlashingiz mumkin (O'zbekiston Shaxsiy ma'lumotlarni muhofaza qilish "
        "to'g'risidagi qonuniga muvofiq).\n\n"
        "Bizning maxfiylik kelishuvimizga rozimisiz?"
    )
    await update.message.reply_text(
        consent_text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Roziman (Accept)", callback_data="consent_accept"),
                InlineKeyboardButton("❌ Rad etaman (Decline)", callback_data="consent_decline")
            ]
        ]),
        parse_mode="Markdown",
    )
    return CONSENT


async def consent_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "consent_accept":
        user = query.from_user
        await create_user(user.id, user.username or "", user.full_name)

        await query.message.reply_text(
            "Rahmat! Ro'yxatdan o'tishni davom ettiramiz.\n\n"
            "*1/3:* Yoshingiz qaysi guruhda?",
            reply_markup=ReplyKeyboardMarkup(
                [["<18", "18-30"], ["30-50", "50+"]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
            parse_mode="Markdown",
        )
        await query.edit_message_text("✅ Maxfiylik kelishuviga rozilik berildi.")
        return AGE
    else:
        await query.edit_message_text(
            "❌ Afsuski, maxfiylik kelishuvini qabul qilmasangiz, botdan foydalana olmaysiz.\n"
            "Agar fikringiz o'zgarsa, istalgan vaqtda qayta /start buyrug'ini bosing."
        )
        return ConversationHandler.END


async def ask_uzsl_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["age_group"] = update.message.text
    await update.message.reply_text(
        "*2/3:* UZSL bilish darajangiz?",
        reply_markup=ReplyKeyboardMarkup(
            [["Boshlang'ich"], ["O'rta"], ["Mutaxassis (ona tili)"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
        parse_mode="Markdown",
    )
    return UZSL_LEVEL


async def ask_is_deaf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["uzsl_level"] = UZSL_LEVEL_MAP.get(update.message.text, "beginner")
    await update.message.reply_text(
        "*3/3:* Siz kar yoki soqovmisiz?",
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
        context.user_data.get("age_group", ""),
        context.user_data.get("uzsl_level", "beginner"),
        is_deaf,
    )
    context.user_data.clear()

    await update.message.reply_text(
        "✅ Ro'yxatdan o'tdingiz! Rahmat.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await update.message.reply_text(
        "Endi video yuborishni boshlang 👇",
        reply_markup=main_menu_kb(),
    )
    return ConversationHandler.END


async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Bekor qilindi. Qaytadan boshlash uchun /start.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# --- /delete_my_data ---

async def delete_my_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚠️ Bu amal sizning profilingiz, barcha videolaringiz va yutuqlaringizni "
        "butunlay o'chiradi. Bu *qaytarib bo'lmaydi*.\n\nDavom etamizmi?",
        reply_markup=confirm_delete_kb(),
        parse_mode="Markdown",
    )


async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "del_confirm":
        await delete_user_data(query.from_user.id)
        await query.edit_message_text(
            "🗑 Ma'lumotlaringiz to'liq o'chirildi. Qaytadan qo'shilish uchun /start."
        )
    else:
        await query.edit_message_text("Bekor qilindi. Ma'lumotlaringiz saqlanib qoldi.")


registration_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        CONSENT: [CallbackQueryHandler(consent_response, pattern="^consent_")],
        AGE: [MessageHandler(filters.Regex(r"^(<18|18-30|30-50|50\+)$"), ask_uzsl_level)],
        UZSL_LEVEL: [MessageHandler(filters.Regex("^(Boshlang'ich|O'rta|Mutaxassis.*)$"), ask_is_deaf)],
        IS_DEAF: [MessageHandler(filters.Regex("^(Ha|Yo'q)$"), finish_registration)],
    },
    fallbacks=[CommandHandler("cancel", cancel_registration)],
    name="registration",
    persistent=True,
)

delete_data_handler = CommandHandler("delete_my_data", delete_my_data)
delete_callback_handler = CallbackQueryHandler(handle_delete_callback, pattern="^del_")
