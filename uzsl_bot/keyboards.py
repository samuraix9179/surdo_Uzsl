from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import REJECTION_REASONS


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Video yuborish", callback_data="menu_submit")],
        [
            InlineKeyboardButton("📚 Belgilar", callback_data="menu_labels"),
            InlineKeyboardButton("👤 Profil", callback_data="menu_profile"),
        ],
        [
            InlineKeyboardButton("🏆 Reyting", callback_data="menu_leaderboard"),
            InlineKeyboardButton("ℹ️ Yordam", callback_data="menu_help"),
        ],
    ])


def categories_kb() -> InlineKeyboardMarkup:
    from config import CATEGORIES
    buttons = []
    current_row = []
    
    # Barcha kategoriyalarni 2 tadan qilib joylashtiramiz (erkin_tarjima dan tashqari)
    for key, label in CATEGORIES.items():
        if key == "erkin_tarjima":
            continue
        current_row.append(InlineKeyboardButton(label, callback_data=f"cat_{key}"))
        if len(current_row) == 2:
            buttons.append(current_row)
            current_row = []
            
    if current_row:
        buttons.append(current_row)
        
    # Erkin tarjima va bekor qilish tugmalari
    buttons.append([InlineKeyboardButton("✍️ Lug'atda yo'q so'z (Erkin)", callback_data="cat_free")])
    buttons.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="submit_cancel")])
    return InlineKeyboardMarkup(buttons)


def labels_kb(labels) -> InlineKeyboardMarkup:
    buttons = []
    for label in labels:
        progress = f"{label['current_count']}/{label['target_count']}"
        buttons.append([InlineKeyboardButton(
            f"{label['word_uz']}  ({progress})",
            callback_data=f"label_{label['label_id']}",
        )])
    buttons.append([
        InlineKeyboardButton("« Orqaga", callback_data="submit_back_to_categories"),
        InlineKeyboardButton("❌ Bekor qilish", callback_data="submit_cancel"),
    ])
    return InlineKeyboardMarkup(buttons)


def waiting_video_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤷 Bu belgini bilmayman", callback_data="skip_label")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="submit_cancel")],
    ])


def moderation_kb(video_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"mod_approve_{video_id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"mod_reject_{video_id}"),
        ],
        [InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="mod_skip")],
    ])


def rejection_reasons_kb(video_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for key, text in REJECTION_REASONS.items():
        buttons.append([InlineKeyboardButton(text, callback_data=f"rej_{key}_{video_id}")])
    buttons.append([InlineKeyboardButton("« Orqaga", callback_data=f"rejback_{video_id}")])
    return InlineKeyboardMarkup(buttons)


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton("✅ Moderatsiya", callback_data="admin_moderate")],
        [InlineKeyboardButton("📦 Eksport (JSON)", callback_data="admin_export")],
    ])


def confirm_delete_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑 Ha, o'chir", callback_data="del_confirm"),
            InlineKeyboardButton("« Bekor qilish", callback_data="del_cancel"),
        ],
    ])
