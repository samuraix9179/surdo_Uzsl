import asyncio
import io
import json
from functools import wraps
from typing import Tuple

from telegram import Update
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters,
)
from telegram.constants import ParseMode

from database import (
    get_pending_videos, moderate_video, get_video_owner,
    get_global_stats, get_label_distribution, add_label,
    get_approved_videos_metadata, get_all_user_ids, set_user_blocked,
    get_label_by_id, set_example_video,
)
from config import ADMIN_IDS, REJECTION_REASONS
from keyboards import moderation_kb, rejection_reasons_kb, admin_menu_kb


def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if uid not in ADMIN_IDS:
            if update.message:
                await update.message.reply_text("⛔ Bu komanda faqat adminlar uchun.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Sizda ruxsat yo'q", show_alert=True)
            return
        return await func(update, context)
    return wrapper


# ------------------- ADMIN PANEL -------------------

@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔧 *Admin panel*\n\nQuyidagilardan birini tanlang:",
        reply_markup=admin_menu_kb(),
        parse_mode=ParseMode.MARKDOWN,
    )


# ------------------- STATISTIKA -------------------

async def _stats_text() -> str:
    s = await get_global_stats()
    dist = await get_label_distribution()

    quality = 0
    moderated = (s["videos_approved"] + s["videos_rejected"])
    if moderated:
        quality = s["videos_rejected"] / moderated * 100

    lines = [
        "📊 *Umumiy statistika*\n",
        f"👥 Foydalanuvchilar: {s['users']}",
        f"🎬 Jami videolar: {s['videos_total']}",
        f"✅ Tasdiqlangan: {s['videos_approved']}",
        f"⏳ Kutilmoqda: {s['videos_pending']}",
        f"❌ Rad etilgan: {s['videos_rejected']}",
        f"📉 Sifatsiz video foizi: {quality:.1f}%",
        f"🏁 Tugagan belgilar: {s['labels_done']}/{s['labels_total']}\n",
        "*Eng kam videoga ega 10 belgi:*",
    ]
    for lb in dist[:10]:
        lines.append(f"▫️ {lb['word_uz']} — {lb['current_count']}/{lb['target_count']}")
    return "\n".join(lines)


@admin_only
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(await _stats_text(), parse_mode=ParseMode.MARKDOWN)


# ------------------- MODERATSIYA -------------------

async def _send_next_pending(message, context):
    videos = await get_pending_videos(limit=1)
    if not videos:
        await message.reply_text("✅ Barcha videolar moderatsiyadan o'tgan!")
        return
    v = videos[0]
    await message.reply_video(
        v["telegram_file_id"],
        caption=(
            f"📹 *Belgi:* {v['word_uz']}\n"
            f"👤 *Foydalanuvchi:* {v['user_name']}\n"
            f"⏱ *Davomiyligi:* {v['duration_seconds']}s\n"
            f"📅 *Yuborilgan:* {v['submitted_at']}\n"
            f"🆔 video\\_id: {v['video_id']}"
        ),
        reply_markup=moderation_kb(v["video_id"]),
        parse_mode=ParseMode.MARKDOWN,
    )


@admin_only
async def moderate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_next_pending(update.message, context)


async def _notify_user(context, user_id, text):
    try:
        await context.bot.send_message(user_id, text, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        pass  # foydalanuvchi botni bloklagan bo'lishi mumkin


@admin_only
async def moderation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "mod_skip":
        await query.answer("O'tkazib yuborildi")
        await _send_next_pending(query.message, context)
        return

    parts = data.split("_")  # mod_approve_<id> | mod_reject_<id>
    action, video_id = parts[1], int(parts[2])

    if action == "approve":
        await query.answer("Tasdiqlandi ✅")
        await moderate_video(video_id, "approved", query.from_user.id)

        # Orqa fonda Hugging Face platformasiga sinxronlash (video + landmark + metadata)
        from utils.sync_to_huggingface import sync_video_to_huggingface
        asyncio.create_task(sync_video_to_huggingface(video_id))

        await query.edit_message_caption(
            caption=(query.message.caption or "") + "\n\n✅ *TASDIQLANDI*",
            parse_mode=ParseMode.MARKDOWN,
        )
        owner = await get_video_owner(video_id)
        if owner:
            await _notify_user(context, owner, "✅ Videongiz tasdiqlandi! Rahmat 🙏")
        await _send_next_pending(query.message, context)

    elif action == "reject":
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=rejection_reasons_kb(video_id))


@admin_only
async def rejection_reason_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("rejback_"):
        video_id = int(data.split("_")[1])
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=moderation_kb(video_id))
        return

    # rej_<key>_<id>
    parts = data.split("_")
    reason_key, video_id = parts[1], int(parts[2])
    reason_text = REJECTION_REASONS.get(reason_key, "Sifati past")

    await query.answer("Rad etildi ❌")
    await moderate_video(video_id, "rejected", query.from_user.id, reason_text)
    await query.edit_message_caption(
        caption=(query.message.caption or "") + f"\n\n❌ *RAD ETILDI:* {reason_text}",
        parse_mode=ParseMode.MARKDOWN,
    )
    owner = await get_video_owner(video_id)
    if owner:
        await _notify_user(
            context, owner,
            f"❌ Afsuski videongiz rad etildi.\nSabab: _{reason_text}_\n\n"
            "Iltimos, qaytadan urinib ko'ring: /submit",
        )
    await _send_next_pending(query.message, context)


# ------------------- LABEL QO'SHISH -------------------

ADD_WORD = 100


@admin_only
async def addlabel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Yangi belgi qo'shish. Formatda yuboring:\n"
        "`word_uz | word_ru | category`\n\n"
        "Masalan: `kitob | книга | tovar`\n\n"
        "Bekor qilish: /cancel",
        parse_mode=ParseMode.MARKDOWN,
    )
    return ADD_WORD


async def addlabel_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = [p.strip() for p in update.message.text.split("|")]
    word_uz = parts[0]
    word_ru = parts[1] if len(parts) > 1 else None
    category = parts[2] if len(parts) > 2 else "boshqa"

    if not word_uz:
        await update.message.reply_text("So'z bo'sh bo'lmasligi kerak. Qayta yuboring yoki /cancel.")
        return ADD_WORD

    try:
        await add_label(word_uz, word_ru, category if category else "boshqa")
        await update.message.reply_text(f"✅ '{word_uz}' belgisi qo'shildi.")
    except Exception:
        await update.message.reply_text(f"⚠️ '{word_uz}' allaqachon mavjud yoki xato yuz berdi.")
    return ConversationHandler.END


async def addlabel_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi.")
    return ConversationHandler.END


# ------------------- BROADCAST -------------------

BROADCAST_MSG = 200


@admin_only
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing.\n"
        "Bekor qilish: /cancel"
    )
    return BROADCAST_MSG


async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_ids = await get_all_user_ids(only_active=True)

    await update.message.reply_text(f"⏳ {len(user_ids)} foydalanuvchiga yuborilmoqda...")

    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await context.bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
            await set_user_blocked(uid, True)
        await asyncio.sleep(0.05)  # flood limitdan saqlanish

    await update.message.reply_text(f"✅ Yuborildi: {sent}\n❌ Yuborilmadi: {failed}")
    return ConversationHandler.END


async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Broadcast bekor qilindi.")
    return ConversationHandler.END


# ------------------- MISOL VIDEO YUKLASH -------------------

EXAMPLE_WAIT_VIDEO = 300


@admin_only
async def upload_example_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/upload_example <label_id> — belgi uchun namuna video yuklash."""
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text(
            "Foydalanish: `/upload_example <label_id>`\n\n"
            "label_id ni /labels yoki /stats orqali bilib oling.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    label_id = int(args[0])
    label = await get_label_by_id(label_id)
    if not label:
        await update.message.reply_text(f"⚠️ label_id={label_id} topilmadi.")
        return ConversationHandler.END

    context.user_data["example_label_id"] = label_id
    await update.message.reply_text(
        f"📹 <b>{label['word_uz']}</b> belgisi uchun namuna videoni yuboring.\n"
        "Bu video foydalanuvchilarga 'qanday ko'rsatish kerak' deb ko'rsatiladi.\n\n"
        "Bekor qilish: /cancel",
        parse_mode=ParseMode.HTML,
    )
    return EXAMPLE_WAIT_VIDEO


async def upload_example_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.video_note
    if not video:
        await update.message.reply_text("Iltimos, video yuboring yoki /cancel.")
        return EXAMPLE_WAIT_VIDEO

    label_id = context.user_data.get("example_label_id")
    if not label_id:
        await update.message.reply_text("Sessiya muddati tugadi. Qaytadan /upload_example.")
        return ConversationHandler.END

    await set_example_video(label_id, video.file_id)
    label = await get_label_by_id(label_id)
    context.user_data.pop("example_label_id", None)

    await update.message.reply_text(
        f"✅ '{label['word_uz']}' uchun namuna video saqlandi.\n"
        "Endi foydalanuvchilar shu belgini tanlaganda namunani ko'radi."
    )
    return ConversationHandler.END


async def upload_example_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("example_label_id", None)
    await update.message.reply_text("Namuna yuklash bekor qilindi.")
    return ConversationHandler.END


# ------------------- EKSPORT (JSON metadata) -------------------


async def _export_json() -> Tuple[io.BytesIO, int]:
    rows = await get_approved_videos_metadata()
    data = [dict(r) for r in rows]
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    buf = io.BytesIO(payload.encode("utf-8"))
    buf.seek(0)
    return buf, len(data)


@admin_only
async def export_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buf, count = await _export_json()
    if count == 0:
        await update.message.reply_text("Tasdiqlangan video yo'q.")
        return
    await update.message.reply_document(
        document=buf, filename="uzsl_metadata.json",  # type: ignore
        caption=f"📦 {count} ta tasdiqlangan video metadata'si.\n"
                "Videolarni yuklab olish: `python -m utils.export`",
        parse_mode=ParseMode.MARKDOWN,
    )


# ------------------- ADMIN MENU CALLBACK -------------------

@admin_only
async def admin_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "admin_stats":
        await query.message.reply_text(await _stats_text(), parse_mode=ParseMode.MARKDOWN)
    elif data == "admin_moderate":
        await _send_next_pending(query.message, context)
    elif data == "admin_export":
        buf, count = await _export_json()
        if count == 0:
            await query.message.reply_text("Tasdiqlangan video yo'q.")
        else:
            await query.message.reply_document(
                document=buf, filename="uzsl_metadata.json",
                caption=f"📦 {count} ta tasdiqlangan video metadata'si.",
            )


# ------------------- HANDLERLAR -------------------

admin_panel_handler = CommandHandler("admin", admin_panel)
stats_handler = CommandHandler("stats", stats_cmd)
moderate_handler = CommandHandler("moderate", moderate_cmd)
export_handler = CommandHandler("export", export_cmd)

moderation_action_handler = CallbackQueryHandler(
    moderation_callback, pattern=r"^mod_(approve|reject|skip)"
)
rejection_handler = CallbackQueryHandler(
    rejection_reason_callback, pattern=r"^(rej_|rejback_)"
)
admin_menu_handler = CallbackQueryHandler(
    admin_menu_callback, pattern=r"^admin_(stats|moderate|export)$"
)

addlabel_conv = ConversationHandler(
    entry_points=[CommandHandler("addlabel", addlabel_start)],
    states={ADD_WORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, addlabel_save)]},
    fallbacks=[CommandHandler("cancel", addlabel_cancel)],
)

broadcast_conv = ConversationHandler(
    entry_points=[CommandHandler("broadcast", broadcast_start)],
    states={BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_send)]},
    fallbacks=[CommandHandler("cancel", broadcast_cancel)],
)

upload_example_conv = ConversationHandler(
    entry_points=[CommandHandler("upload_example", upload_example_start)],
    states={
        EXAMPLE_WAIT_VIDEO: [
            MessageHandler(filters.VIDEO | filters.VIDEO_NOTE, upload_example_save),
        ],
    },
    fallbacks=[CommandHandler("cancel", upload_example_cancel)],
)
