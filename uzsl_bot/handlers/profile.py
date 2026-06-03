from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from utils.grammar_translator import translate_uzsl_to_uzbek

from database import (
    get_user, get_user_stats, get_leaderboard, get_all_labels,
)
from config import BADGES, UZSL_LEVEL_LABELS, ADMIN_IDS
from keyboards import main_menu_kb

HELP_TEXT = (
    "ℹ️ *UZSL Dataset Bot — Yordam*\n\n"
    "Bu bot O'zbek imo-ishora tili videolarini yig'adi. "
    "Har bir video kar va soqovlar uchun tarjimon ilovasini o'rgatishga yordam beradi.\n\n"
    "*Komandalar:*\n"
    "/start — Boshlash / asosiy menyu\n"
    "/submit — Video yuborish\n"
    "/labels — Belgilar ro'yxati va progress\n"
    "/profile — Profil va statistika\n"
    "/leaderboard — Top hissa qo'shuvchilar\n"
    "/delete\\_my\\_data — Ma'lumotlarni o'chirish\n"
    "/help — Shu yordam\n\n"
    "*Mukofotlar:*\n"
    "🥉 10 video — Faol ko'ngilli\n"
    "🥈 50 video — Senior contributor (+sertifikat)\n"
    "🥇 100 video — UZSL qahramoni (+sertifikat)\n"
    "💎 250 video — Legendary contributor (+sertifikat)"
)

ADMIN_HELP_TEXT = (
    "\n\n*Admin komandalari:*\n"
    "/admin — Admin panel\n"
    "/moderate — Videolarni moderatsiya\n"
    "/stats — Statistika\n"
    "/addlabel — Yangi belgi qo'shish\n"
    "/upload\\_example — Belgi uchun namuna video\n"
    "/broadcast — E'lon yuborish\n"
    "/export — Metadata JSON"
)


def _profile_text(user, stats) -> str:
    approved = stats["approved"] or 0
    earned = [f"{e} {n}" for t, (e, n, _) in BADGES.items() if approved >= t]
    badges_text = "\n".join(earned) if earned else "_Hali yo'q_"

    next_badge = next(
        ((t, e, n) for t, (e, n, _) in sorted(BADGES.items()) if approved < t), None
    )
    next_goal = (
        f"\n🎯 Keyingi: {next_badge[1]} {next_badge[2]} ({next_badge[0]} ta video)"
        if next_badge else "\n🎯 Barcha darajalarni egalladingiz!"
    )

    level = UZSL_LEVEL_LABELS.get(user["uzsl_level"], user["uzsl_level"] or "—")

    return (
        f"👤 *Sizning profilingiz*\n\n"
        f"Ism: {user['full_name']}\n"
        f"UZSL darajasi: {level}\n"
        f"Yosh guruhi: {user['age_group'] or '—'}\n\n"
        f"📊 *Statistika:*\n"
        f"Jami yuborilgan: {stats['total'] or 0}\n"
        f"✅ Tasdiqlangan: {approved}\n"
        f"⏳ Ko'rib chiqilmoqda: {stats['pending'] or 0}\n"
        f"❌ Rad etilgan: {stats['rejected'] or 0}\n\n"
        f"🏆 *Yutuqlar:*\n{badges_text}{next_goal}"
    )


async def _send_profile(message, user_id):
    user = await get_user(user_id)
    if not user:
        await message.reply_text("Avval /start orqali ro'yxatdan o'ting.")
        return
    stats = await get_user_stats(user_id)
    await message.reply_text(_profile_text(user, stats), parse_mode="Markdown")


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_profile(update.message, update.effective_user.id)


def _leaderboard_text(top) -> str:
    if not top:
        return "Hozircha hech kim video yubormagan."
    medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 7
    lines = ["🏆 *Top 10 hissa qo'shuvchilar*\n"]
    for i, u in enumerate(top):
        lines.append(
            f"{medals[i]} {u['full_name']} — "
            f"{u['videos_approved']} tasdiqlangan ({u['videos_submitted']} jami)"
        )
    return "\n".join(lines)


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = await get_leaderboard(10)
    await update.message.reply_text(_leaderboard_text(top), parse_mode="Markdown")


def _labels_text(labels) -> str:
    lines = ["📚 *Belgilar ro'yxati* (progress)\n"]
    by_cat = {}
    for lb in labels:
        by_cat.setdefault(lb["category"] or "boshqa", []).append(lb)
    for cat, items in by_cat.items():
        lines.append(f"\n*{cat.capitalize()}:*")
        for lb in items:
            done = "✅" if lb["current_count"] >= lb["target_count"] else "▫️"
            lines.append(f"{done} {lb['word_uz']} — {lb['current_count']}/{lb['target_count']}")
    return "\n".join(lines)


async def labels_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    labels = await get_all_labels()
    text = _labels_text(labels)
    # Telegram 4096 belgi limiti — kerak bo'lsa bo'lib yuboramiz
    for chunk in _split_message(text):
        await update.message.reply_text(chunk, parse_mode="Markdown")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = HELP_TEXT
    if update.effective_user.id in ADMIN_IDS:
        text += ADMIN_HELP_TEXT
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=main_menu_kb()
    )


def _split_message(text, limit=4000):
    lines = text.split("\n")
    chunks, current = [], ""
    for line in lines:
        if len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = ""
        current += line + "\n"
    if current:
        chunks.append(current)
    return chunks


# --- Menyu (inline) callbacklari ---

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_profile":
        await _send_profile(query.message, query.from_user.id)
    elif data == "menu_leaderboard":
        top = await get_leaderboard(10)
        await query.message.reply_text(_leaderboard_text(top), parse_mode="Markdown")
    elif data == "menu_labels":
        labels = await get_all_labels()
        for chunk in _split_message(_labels_text(labels)):
            await query.message.reply_text(chunk, parse_mode="Markdown")
    elif data == "menu_help":
        text = HELP_TEXT
        if query.from_user.id in ADMIN_IDS:
            text += ADMIN_HELP_TEXT
        await query.message.reply_text(text, parse_mode="Markdown")


async def translate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "✍️ *UZSL Aqlli Tarjimon*\n\n"
            "Foydalanish: `/translate <so'zlar ketma-ketligi>`\n"
            "Masalan: `/translate men do'kon bormoq`",
            parse_mode="Markdown"
        )
        return

    sentence = translate_uzsl_to_uzbek(args)
    await update.message.reply_text(
        f"📝 *UZSL:* `{' '.join(args)}`\n"
        f"🔄 *O'zbekcha tarjimasi:* *{sentence}*",
        parse_mode="Markdown"
    )


profile_handler = CommandHandler("profile", profile)
leaderboard_handler = CommandHandler("leaderboard", leaderboard)
labels_handler = CommandHandler("labels", labels_list)
help_handler = CommandHandler("help", help_cmd)
translate_handler = CommandHandler("translate", translate_cmd)
# menu_submit submit_handler tomonidan boshqariladi
menu_callback_handler = CallbackQueryHandler(
    menu_callback, pattern="^menu_(profile|leaderboard|labels|help)$"
)
