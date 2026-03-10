from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, Contact
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS
from database import get_user, save_user, get_channels, add_channel, remove_channel, get_all_users
from keyboards import (
    lang_keyboard, subscribe_keyboard, phone_keyboard,
    main_menu_keyboard, settings_keyboard, settings_inline_keyboard,
    settings_info_text, admin_keyboard, back_keyboard
)
from states import RegisterState, AdminState, SettingsState
from texts import t, TEXTS

router = Router()



async def check_subscriptions(bot: Bot, user_id: int) -> bool:
    """Check if user is subscribed to all required channels"""
    channels = get_channels()
    if not channels:
        return True
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch["channel_id"], user_id)
            if member.status in ("left", "kicked", "banned"):
                return False
        except Exception:
            return False
    return True


def get_lang(user_id: int) -> str:
    user = get_user(user_id)
    if user and "lang" in user:
        return user["lang"]
    return "uz"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id

    # Admin check
    if user_id in ADMIN_IDS:
        user = get_user(user_id)
        if user and user.get("registered"):
            lang = user.get("lang", "uz")
            await message.answer("👨‍💼 Xush kelibsiz, Admin!", reply_markup=main_menu_keyboard(lang))
            return

    user = get_user(user_id)

    if user and user.get("registered"):
        lang = user.get("lang", "uz")
        await message.answer(t(lang, "main_menu"), reply_markup=main_menu_keyboard(lang))
        return

    channels = get_channels()
    if channels:
        subscribed = await check_subscriptions(bot, user_id)
        if not subscribed:
            await message.answer(
                t("uz", "subscribe_required"),
                reply_markup=subscribe_keyboard(channels)
            )
            return

    # Ask language
    await state.set_state(RegisterState.choosing_lang)
    await message.answer(t("uz", "choose_lang"), reply_markup=lang_keyboard())



@router.callback_query(F.data == "check_subscribe")
async def check_subscribe_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    subscribed = await check_subscriptions(bot, user_id)

    if not subscribed:
        channels = get_channels()
        await callback.answer(t("uz", "not_subscribed"), show_alert=True)
        return

    await callback.message.delete()

    user = get_user(user_id)
    if user and user.get("registered"):
        lang = user.get("lang", "uz")
        await callback.message.answer(t(lang, "main_menu"), reply_markup=main_menu_keyboard(lang))
        return

    await state.set_state(RegisterState.choosing_lang)
    await callback.message.answer(t("uz", "choose_lang"), reply_markup=lang_keyboard())

@router.callback_query(RegisterState.choosing_lang, F.data.startswith("lang_"))
async def choose_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]  # "uz" or "ru"

    await state.update_data(lang=lang)
    await callback.message.delete()
    await callback.answer(t(lang, "lang_selected"))

    await state.set_state(RegisterState.entering_name)
    await callback.message.answer(t(lang, "enter_name"))


# =================== REGISTRATION ===================

@router.message(RegisterState.entering_name)
async def enter_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    name = message.text.strip()
    if not name or len(name) < 2:
        await message.answer("❌ Iltimos, to'g'ri ism kiriting (kamida 2 ta harf):")
        return

    await state.update_data(name=name)
    await state.set_state(RegisterState.entering_surname)
    await message.answer(t(lang, "enter_surname"))


@router.message(RegisterState.entering_surname)
async def enter_surname(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    surname = message.text.strip()
    if not surname or len(surname) < 2:
        await message.answer("❌ Iltimos, to'g'ri familiya kiriting (kamida 2 ta harf):")
        return

    await state.update_data(surname=surname)
    await state.set_state(RegisterState.entering_phone)
    await message.answer(t(lang, "enter_phone"), reply_markup=phone_keyboard(lang))


@router.message(RegisterState.entering_phone, F.contact)
async def enter_phone_contact(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    contact: Contact = message.contact
    phone = contact.phone_number

    await finish_registration(message, state, data, phone, lang)


@router.message(RegisterState.entering_phone, F.text)
async def enter_phone_text(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    phone = message.text.strip()

    # Basic phone validation
    cleaned = phone.replace("+", "").replace(" ", "").replace("-", "")
    if not cleaned.isdigit() or len(cleaned) < 9:
        await message.answer("❌ Iltimos, to'g'ri telefon raqam kiriting:")
        return

    await finish_registration(message, state, data, phone, lang)


async def finish_registration(message: Message, state: FSMContext, data: dict, phone: str, lang: str):
    user_id = message.from_user.id
    name = data.get("name")
    surname = data.get("surname")

    user_data = {
        "user_id": user_id,
        "username": message.from_user.username,
        "lang": lang,
        "name": name,
        "surname": surname,
        "phone": phone,
        "registered": True
    }
    save_user(user_id, user_data)

    await state.clear()
    await message.answer(
        t(lang, "registration_done", name=name, surname=surname, phone=phone),
        reply_markup=main_menu_keyboard(lang)
    )

@router.message(F.text.in_(["💱 Valyuta ayirboshlash", "💱 Обмен валют"]))
async def menu_exchange(message: Message):
    lang = get_lang(message.from_user.id)
    await message.answer(t(lang, "exchange_menu"))


@router.message(F.text.in_(["📊 Kurs", "📊 Курс"]))
async def menu_rates(message: Message, bot: Bot):
    lang = get_lang(message.from_user.id)
    try:
        from rates_api import get_rates_text, update_live_rates, get_live_rates
        # Kurslar DB da yo'q bo'lsa yangilaydi
        if not get_live_rates():
            wait_msg = await message.answer("⏳ Kurslar yuklanmoqda...")
            await update_live_rates()
            try:
                await wait_msg.delete()
            except:
                pass
        text = get_rates_text(lang)
        if not text or text.startswith("⏳"):
            text = "❌ Kurs ma'lumotlari hali yuklanmagan. Keyinroq urinib ko'ring." if lang == "uz" else "❌ Данные курсов ещё не загружены. Попробуйте позже."
    except Exception as e:
        import logging;
        logging.getLogger(__name__).warning(f"Kurs handler xato: {e}")
        text = "❌ Kurs ma'lumotlari yuklanmadi. Qayta urinib ko'ring." if lang == "uz" else "❌ Не удалось загрузить курсы. Попробуйте ещё раз."
    await message.answer(text)


@router.message(F.text.in_(["👥 Hamënlar", "👥 Партнёры"]))
async def menu_partners(message: Message):
    lang = get_lang(message.from_user.id)
    await message.answer(t(lang, "partners_menu"))


@router.message(F.text.in_(["👥 Referal", "👥 Реферал"]))
async def menu_referral(message: Message):
    lang = get_lang(message.from_user.id)
    await message.answer(t(lang, "referral_menu"))


@router.message(F.text.in_(["📞 Qayta aloqa", "📞 Обратная связь"]))
async def menu_callback(message: Message):
    lang = get_lang(message.from_user.id)
    await message.answer(t(lang, "callback_menu"))


@router.message(F.text.in_(["🔄 Almashuvlar", "🔄 Переводы"]))
async def menu_transfers(message: Message):
    lang = get_lang(message.from_user.id)
    await message.answer(t(lang, "transfers_menu"))


@router.message(F.text.in_(["📖 Qo`llanma", "📖 Руководство"]))
async def menu_guide(message: Message):
    lang = get_lang(message.from_user.id)
    await message.answer(t(lang, "guide_menu"))

@router.message(F.text.in_(["⚙️ Sozlamalar", "⚙️ Настройки"]))
async def menu_settings(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    user = get_user(user_id)
    await state.set_state(SettingsState.in_settings)
    text = settings_info_text(user, lang)
    await message.answer(text, reply_markup=settings_inline_keyboard(lang))


@router.callback_query(F.data == "settings_lang")
async def settings_change_lang(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RegisterState.choosing_lang)
    await state.update_data(changing_lang=True)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(t("uz", "choose_lang"), reply_markup=lang_keyboard())
    await callback.answer()


@router.callback_query(F.data == "settings_name")
async def settings_change_name_cb(callback: CallbackQuery, state: FSMContext):
    lang = get_lang(callback.from_user.id)
    await state.set_state(SettingsState.changing_name)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(t(lang, "enter_name"))
    await callback.answer()


@router.callback_query(F.data == "settings_phone")
async def settings_change_phone_cb(callback: CallbackQuery, state: FSMContext):
    lang = get_lang(callback.from_user.id)
    await state.set_state(SettingsState.changing_phone)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(t(lang, "enter_phone"), reply_markup=phone_keyboard(lang))
    await callback.answer()


@router.message(SettingsState.changing_name)
async def change_name_finish(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    name = message.text.strip()

    if not name or len(name) < 2:
        await message.answer("❌ Iltimos, to'g'ri ism kiriting:")
        return

    user = get_user(user_id)
    user["name"] = name
    save_user(user_id, user)

    await state.clear()
    text = settings_info_text(get_user(user_id), lang)
    await message.answer(text, reply_markup=settings_inline_keyboard(lang))


@router.message(SettingsState.changing_phone, F.contact)
async def change_phone_contact(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    user = get_user(user_id)
    user["phone"] = message.contact.phone_number
    save_user(user_id, user)
    await state.clear()
    text = settings_info_text(get_user(user_id), lang)
    await message.answer(text, reply_markup=settings_inline_keyboard(lang))


@router.message(SettingsState.changing_phone, F.text)
async def change_phone_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    phone = message.text.strip()
    cleaned = phone.replace("+", "").replace(" ", "").replace("-", "")
    if not cleaned.isdigit() or len(cleaned) < 9:
        await message.answer("❌ Iltimos, to'g'ri telefon raqam kiriting:")
        return
    user = get_user(user_id)
    user["phone"] = phone
    save_user(user_id, user)
    await state.clear()
    text = settings_info_text(get_user(user_id), lang)
    await message.answer(text, reply_markup=settings_inline_keyboard(lang))


@router.message(F.text.in_(["🔙 Orqaga", "🔙 Назад"]))
async def go_back(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    await state.clear()
    await message.answer(t(lang, "main_menu"), reply_markup=main_menu_keyboard(lang))


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("👨‍💼 Admin panel", reply_markup=admin_keyboard())


@router.message(F.text == "➕ Kanal qo'shish")
async def admin_add_channel_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AdminState.waiting_channel_id)
    await message.answer("Kanal ID sini kiriting (masalan: -1001234567890):\n\n💡 Botni kanalga admin qilib qo'shing!")


@router.message(AdminState.waiting_channel_id)
async def admin_add_channel_id(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        channel_id = int(message.text.strip())
        await state.update_data(channel_id=channel_id)
        await state.set_state(AdminState.waiting_channel_link)
        await message.answer("Kanal havolasini kiriting (masalan: https://t.me/kanalim):")
    except ValueError:
        await message.answer("❌ Noto'g'ri format! ID son bo'lishi kerak:")


@router.message(AdminState.waiting_channel_link)
async def admin_add_channel_link(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    link = message.text.strip()
    await state.update_data(channel_link=link)
    await state.set_state(AdminState.waiting_channel_name)
    await message.answer("Kanal nomini kiriting:")


@router.message(AdminState.waiting_channel_name)
async def admin_add_channel_name(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    data = await state.get_data()
    name = message.text.strip()

    result = add_channel(data["channel_id"], data["channel_link"], name)
    await state.clear()

    if result:
        await message.answer(f"✅ Kanal qo'shildi!\n📢 {name}\n🔗 {data['channel_link']}", reply_markup=admin_keyboard())
    else:
        await message.answer("❌ Bu kanal allaqachon mavjud!", reply_markup=admin_keyboard())


@router.message(F.text == "➖ Kanal o'chirish")
async def admin_remove_channel_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    from database import get_channels
    channels = get_channels()
    if not channels:
        await message.answer("📭 Kanallar yo'q!")
        return

    text = "📋 Mavjud kanallar:\n\n"
    for ch in channels:
        text += f"• {ch['channel_name']} | ID: {ch['channel_id']}\n"
    text += "\nO'chirmoqchi bo'lgan kanal ID sini kiriting:"

    await state.set_state(AdminState.waiting_remove_id)
    await message.answer(text)


@router.message(AdminState.waiting_remove_id)
async def admin_remove_channel(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        channel_id = int(message.text.strip())
        result = remove_channel(channel_id)
        await state.clear()
        if result:
            await message.answer("✅ Kanal o'chirildi!", reply_markup=admin_keyboard())
        else:
            await message.answer("❌ Kanal topilmadi!", reply_markup=admin_keyboard())
    except ValueError:
        await message.answer("❌ Noto'g'ri format!")


@router.message(F.text == "📋 Kanallar ro'yxati")
async def admin_list_channels(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    from database import get_channels
    channels = get_channels()
    if not channels:
        await message.answer("📭 Hech qanday kanal qo'shilmagan!")
        return

    text = "📋 Kanallar ro'yxati:\n\n"
    for i, ch in enumerate(channels, 1):
        text += f"{i}. {ch['channel_name']}\n   🔗 {ch['channel_link']}\n   🆔 {ch['channel_id']}\n\n"
    await message.answer(text)


@router.message(F.text == "👥 Foydalanuvchilar")
async def admin_users_count(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    users = get_all_users()
    await message.answer(f"👥 Jami foydalanuvchilar: {len(users)} ta")


@router.message(F.text == "📨 Hammaga xabar")
async def admin_broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AdminState.waiting_broadcast)
    await message.answer("Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:")


@router.message(AdminState.waiting_broadcast)
async def admin_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in ADMIN_IDS:
        return

    users = get_all_users()
    count = 0
    for user_id_str in users:
        try:
            await bot.send_message(int(user_id_str), message.text)
            count += 1
        except Exception:
            pass

    await state.clear()
    await message.answer(f"✅ Xabar {count} ta foydalanuvchiga yuborildi!", reply_markup=admin_keyboard())


@router.callback_query(F.data.startswith("lang_"))
async def handle_lang_callback(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id

    current_state = await state.get_state()
    data = await state.get_data()

    if current_state == RegisterState.choosing_lang:
        if data.get("changing_lang"):
            # Just updating language
            user = get_user(user_id)
            if user:
                user["lang"] = lang
                save_user(user_id, user)
            await state.clear()
            await callback.message.delete()
            await callback.answer(f"✅ Til o'zgartirildi!")
            await callback.message.answer(t(lang, "main_menu"), reply_markup=main_menu_keyboard(lang))
        else:
            await state.update_data(lang=lang)
            await callback.message.delete()
            await callback.answer(t(lang, "lang_selected"))
            await state.set_state(RegisterState.entering_name)
            await callback.message.answer(t(lang, "enter_name"))