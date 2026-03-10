from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from texts import t


def settings_info_text(user: dict, lang: str) -> str:
    """Generate settings info text showing user data"""
    lang_name = "O'zbek" if user.get("lang", "uz") == "uz" else "Русский"
    if lang == "ru":
        lang_label = "Язык"
        name_label = "Имя"
        phone_label = "Телефон"
        title = "⚙️ Настройки"
        hint = "Что хотите изменить? 👇"
    else:
        lang_label = "Til"
        name_label = "Ism"
        phone_label = "Telefon"
        title = "⚙️ Sozlamalar"
        hint = "O'zgartirmoqchi bo'lganingizni tanlang 👇"

    name = f"{user.get('name', '')} {user.get('surname', '')}".strip()
    phone = user.get("phone", "—")
    return (
        f"{title}\n\n"
        f"👤 {name_label}: {name}\n"
        f"🌐 {lang_label}: {lang_name}\n"
        f"📞 {phone_label}: {phone}\n\n"
        f"{hint}"
    )


def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        ]
    ])


def subscribe_keyboard(channels: list) -> InlineKeyboardMarkup:
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(
            text=f"📢 {ch['channel_name']}",
            url=ch["channel_link"]
        )])
    buttons.append([InlineKeyboardButton(
        text="✅ Obuna bo'ldim / Я подписался",
        callback_data="check_subscribe"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def phone_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "share_contact"), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t(lang, "exchange")),
                KeyboardButton(text=t(lang, "rates")),
            ],
            [
                KeyboardButton(text=t(lang, "partners")),
                KeyboardButton(text=t(lang, "referral")),
            ],
            [
                KeyboardButton(text=t(lang, "settings")),
                KeyboardButton(text=t(lang, "callback")),
            ],
            [
                KeyboardButton(text=t(lang, "transfers")),
                KeyboardButton(text=t(lang, "guide")),
            ],
        ],
        resize_keyboard=True
    )


def settings_inline_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Inline keyboard for settings menu (like the screenshot)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 " + ("Tilni o'zgartirish" if lang == "uz" else "Изменить язык"), callback_data="settings_lang")],
        [InlineKeyboardButton(text="👤 " + ("Ismni o'zgartirish" if lang == "uz" else "Изменить имя"), callback_data="settings_name")],
        [InlineKeyboardButton(text="📞 " + ("Telefonni o'zgartirish" if lang == "uz" else "Изменить телефон"), callback_data="settings_phone")],
    ])


def settings_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "back"))],
        ],
        resize_keyboard=True
    )


def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Kanal qo'shish"), KeyboardButton(text="➖ Kanal o'chirish")],
            [KeyboardButton(text="📋 Kanallar ro'yxati"), KeyboardButton(text="👥 Foydalanuvchilar")],
            [KeyboardButton(text="📨 Hammaga xabar"), KeyboardButton(text="🔙 Orqaga")],
        ],
        resize_keyboard=True
    )


def back_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "back"))]],
        resize_keyboard=True
    )
