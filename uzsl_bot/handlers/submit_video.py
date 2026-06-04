import time

from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)

from database import (
    get_label_by_id, save_video, get_user,
    get_labels_by_category, get_or_create_custom_label,
)
from config import (
    MIN_VIDEO_DURATION, MAX_VIDEO_DURATION, MAX_FILE_SIZE_MB, VIDEO_COOLDOWN_SECONDS,
)
from keyboards import labels_kb, waiting_video_kb, main_menu_kb, categories_kb
from utils.rewards import check_and_award_badge, generate_certificate

CHOOSE_CATEGORY, CHOOSE_LABEL, WAITING_FREE_TEXT, WAITING_VIDEO = range(10, 14)

INSTRUCTIONS = (
    "📹 Belgi: *{word}*\n\n"
    "*Video yozish bo'yicha qoidalar:*\n"
    "• Davomiyligi: 1-10 soniya\n"
    "• Yorug' joyda turing\n"
    "• Yelka va qo'llaringiz to'liq ko'rinishi kerak\n"
    "• Bitta belgini bir marta sekin va aniq ko'rsating\n"
    "• Kamera mustahkam turishi kerak (tebranmasin)\n\n"
    "Videoni yozib, shu yerga yuboring 👇"
)


async def _show_categories(message, context):
    await message.reply_text(
        "Quyidagi kategoriyalardan birini tanlang yoki lug'atda yo'q so'zni kiritib video yuborish uchun **✍️ Lug'atda yo'q so'z (Erkin)** tugmasini bosing:\n\n"
        "_Kategoriyalar mavjud so'zlarni guruhlab osonroq topish uchun xizmat qiladi._",
        reply_markup=categories_kb(),
        parse_mode="Markdown",
    )
    return CHOOSE_CATEGORY


async def submit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    if not user or not user["age_group"]:
        await update.message.reply_text("Avval /start orqali ro'yxatdan o'ting.")
        return ConversationHandler.END
    return await _show_categories(update.message, context)


async def submit_start_from_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = await get_user(query.from_user.id)
    if not user or not user["age_group"]:
        await query.message.reply_text("Avval /start orqali ro'yxatdan o'ting.")
        return ConversationHandler.END
    return await _show_categories(query.message, context)


async def category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "cat_free":
        await query.message.reply_text(
            "✍️ *Lug'atda yo'q so'z yuborish (Erkin tarjima) rejimiga o'tdingiz.*\n\n"
            "Ushbu videoda qaysi so'z yoki gapni imo-ishorada ko'rsatmoqchisiz? "
            "Iltimos, uning o'zbekcha tarjimasini yozib yuboring (Masalan: *yaxshi boring*, *rahmat*).\n\n"
            "/cancel — bekor qilish",
            parse_mode="Markdown",
        )
        return WAITING_FREE_TEXT

    category = data.split("_")[1]
    context.user_data["current_category"] = category

    return await _show_labels_for_category(query.message, context, category)


async def _show_labels_for_category(message, context, category):
    labels = await get_labels_by_category(category, limit=8)
    if not labels:
        await message.reply_text(
            f"Hozircha '{category}' kategoriyasidagi barcha belgilar uchun yetarli video yig'ilgan. "
            "Boshqa kategoriya tanlang! 🎉",
            reply_markup=categories_kb()
        )
        return CHOOSE_CATEGORY

    cat_title = category.capitalize()
    await message.reply_text(
        f"📂 Kategoriya: *{cat_title}*\n\n"
        "Qaysi belgini ko'rsatmoqchisiz?\n"
        "_Ushbu ro'yxatdagi belgilar eng kam videoga ega bo'lganlar._",
        reply_markup=labels_kb(labels),
        parse_mode="Markdown",
    )
    return CHOOSE_LABEL


async def back_to_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("current_category", None)
    return await _show_categories(query.message, context)


async def receive_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        await update.message.reply_text("Iltimos, faqat matn yuboring.")
        return WAITING_FREE_TEXT

    word_uz = text.strip()
    if len(word_uz) < 2 or len(word_uz) > 60:
        await update.message.reply_text("Matn uzunligi 2 dan 60 tagacha harf bo'lishi kerak. Qaytadan yozing.")
        return WAITING_FREE_TEXT

    label_id = await get_or_create_custom_label(word_uz)
    context.user_data["current_label_id"] = label_id
    context.user_data["current_label_word"] = word_uz
    context.user_data["is_free_translation"] = True

    instructions = INSTRUCTIONS.format(word=word_uz)
    await update.message.reply_text(
        instructions,
        parse_mode="Markdown",
        reply_markup=waiting_video_kb(),
    )
    return WAITING_VIDEO


async def label_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    label_id = int(query.data.split("_")[1])
    label = await get_label_by_id(label_id)
    if not label:
        await query.message.reply_text("Belgi topilmadi. /submit ni qayta urinib ko'ring.")
        return ConversationHandler.END

    context.user_data["current_label_id"] = label_id
    context.user_data["current_label_word"] = label["word_uz"]

    text = INSTRUCTIONS.format(word=label["word_uz"])

    if label["example_video_id"]:
        await query.message.reply_video(
            label["example_video_id"],
            caption=text,
            parse_mode="Markdown",
            reply_markup=waiting_video_kb(),
        )
    else:
        await query.message.reply_text(
            text, parse_mode="Markdown", reply_markup=waiting_video_kb(),
        )
    return WAITING_VIDEO


async def skip_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """'Bu belgini bilmayman' — boshqa belgilar ro'yxatini qayta ko'rsatadi."""
    query = update.callback_query
    await query.answer("Boshqa belgi tanlang")
    category = context.user_data.get("current_category")
    context.user_data.pop("current_label_id", None)
    context.user_data.pop("current_label_word", None)

    if context.user_data.pop("is_free_translation", False) or not category:
        return await _show_categories(query.message, context)

    return await _show_labels_for_category(query.message, context, category)


async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "current_label_id" not in context.user_data:
        await update.message.reply_text("Avval /submit orqali belgini tanlang.")
        return ConversationHandler.END

    video = update.message.video or update.message.video_note
    if not video:
        await update.message.reply_text("Iltimos, video yuboring (matn yoki rasm emas).")
        return WAITING_VIDEO

    # Anti-spam: cooldown
    now = time.monotonic()
    last = context.user_data.get("last_video_ts", 0)
    if now - last < VIDEO_COOLDOWN_SECONDS:
        await update.message.reply_text("⏳ Birozdan keyin urinib ko'ring.")
        return WAITING_VIDEO
    context.user_data["last_video_ts"] = now

    # Validatsiya
    if video.duration < MIN_VIDEO_DURATION:
        await update.message.reply_text(
            f"❌ Video juda qisqa ({video.duration}s).\n"
            f"Minimum {MIN_VIDEO_DURATION:.0f}s bo'lishi kerak. Qaytadan yozing."
        )
        return WAITING_VIDEO

    if video.duration > MAX_VIDEO_DURATION:
        await update.message.reply_text(
            f"❌ Video juda uzun ({video.duration}s).\n"
            f"Maximum {MAX_VIDEO_DURATION:.0f}s bo'lishi kerak. Faqat bitta belgini yozing."
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
        f"✅ Rahmat! Sizning '*{label_word}*' videongiz qabul qilindi.\n"
        "Tez orada moderator tekshirib chiqadi.",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )

    # Mukofot tekshirish
    badge = await check_and_award_badge(user_id)
    if badge:
        await update.message.reply_text(
            f"🎉 Yangi yutuq: {badge['emoji']} *{badge['name']}*!\n"
            f"Siz {badge['threshold']} ta tasdiqlangan videoga yetdingiz!",
            parse_mode="Markdown",
        )
        if badge["has_certificate"]:
            user = await get_user(user_id)
            pdf = generate_certificate(
                user["full_name"] or update.effective_user.first_name,
                badge["name"],
                badge["threshold"],
            )
            if pdf:
                await update.message.reply_document(
                    document=pdf,
                    filename=f"UZSL_sertifikat_{badge['threshold']}.pdf",
                    caption="🏅 Sertifikatingiz tayyor!",
                )

    context.user_data.pop("current_label_id", None)
    context.user_data.pop("current_label_word", None)
    context.user_data.pop("is_free_translation", None)
    context.user_data.pop("current_category", None)
    return ConversationHandler.END


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("current_label_id", None)
    context.user_data.pop("current_label_word", None)
    context.user_data.pop("is_free_translation", None)
    context.user_data.pop("current_category", None)
    await update.message.reply_text("Bekor qilindi.", reply_markup=main_menu_kb())
    return ConversationHandler.END


async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("current_label_id", None)
    context.user_data.pop("current_label_word", None)
    context.user_data.pop("is_free_translation", None)
    context.user_data.pop("current_category", None)
    await query.message.reply_text("Bekor qilindi.", reply_markup=main_menu_kb())
    return ConversationHandler.END


submit_handler = ConversationHandler(
    entry_points=[
        CommandHandler("submit", submit_start),
        CallbackQueryHandler(submit_start_from_menu, pattern="^menu_submit$"),
    ],
    states={
        CHOOSE_CATEGORY: [
            CallbackQueryHandler(category_chosen, pattern="^cat_"),
            CallbackQueryHandler(cancel_callback, pattern="^submit_cancel$"),
        ],
        CHOOSE_LABEL: [
            CallbackQueryHandler(label_chosen, pattern="^label_"),
            CallbackQueryHandler(back_to_categories, pattern="^submit_back_to_categories$"),
            CallbackQueryHandler(cancel_callback, pattern="^submit_cancel$"),
        ],
        WAITING_FREE_TEXT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_free_text),
            CommandHandler("cancel", cancel_cmd),
        ],
        WAITING_VIDEO: [
            MessageHandler(filters.VIDEO | filters.VIDEO_NOTE, receive_video),
            CallbackQueryHandler(skip_label, pattern="^skip_label$"),
            CallbackQueryHandler(cancel_callback, pattern="^submit_cancel$"),
            CommandHandler("cancel", cancel_cmd),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_cmd)],
    name="submit",
    persistent=True,
    per_message=False,
)
