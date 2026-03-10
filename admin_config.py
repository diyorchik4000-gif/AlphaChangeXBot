import logging
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from config import ADMIN_IDS
from database import load_db, save_db, get_all_users, get_channels, add_channel, remove_channel
from exchange_config import CURRENCIES, DEFAULT_RATES, get_currency_by_id

log = logging.getLogger(__name__)
admin_config_router = Router()
CRYPTO_CURS = [c for c in CURRENCIES if c["type"] == "crypto"]

class ACS(StatesGroup):
    api_edit_val  = State()
    man_to        = State()
    man_rate      = State()
    man_min       = State()
    man_max       = State()
    man_comm      = State()
    man_field_val = State()
    card_val      = State()
    ch_id         = State()
    ch_link       = State()
    ch_name       = State()
    ch_del        = State()
    broadcast     = State()



def is_admin(uid): return uid in ADMIN_IDS

def get_settings():
    return load_db().get("rate_settings", {})

def save_settings(s):
    db = load_db(); db["rate_settings"] = s; save_db(db)

def get_cards():
    return load_db().get("payment_cards", {
        "uzcard": "8600 1666 0393 7029",
        "humo":   "9860 0000 0000 0000"
    })

def save_cards(c):
    db = load_db(); db["payment_cards"] = c; save_db(db)

def get_manual():
    return load_db().get("manual_rates", {})

def save_manual(r):
    db = load_db(); db["manual_rates"] = r; save_db(db)

def get_orders():
    return load_db().get("orders", {})

def set_order_status(oid, status):
    db = load_db()
    if str(oid) in db.get("orders", {}):
        db["orders"][str(oid)]["status"] = status
        save_db(db)

def cname(cid):
    c = get_currency_by_id(cid)
    return c["name"] if c else cid

def fmt(v):
    try:
        if isinstance(v, float) and v != int(v):
            return f"{v:.6f}".rstrip("0").rstrip(".")
        return f"{int(v):,}"
    except:
        return str(v)

def admin_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⚙️ API foizlar"),      KeyboardButton(text="💹 Manual kurslar")],
        [KeyboardButton(text="💳 To'lov kartalari"),  KeyboardButton(text="📦 Buyurtmalar")],
        [KeyboardButton(text="📢 Kanallar"),          KeyboardButton(text="👥 Foydalanuvchilar")],
        [KeyboardButton(text="📨 Broadcast"),         KeyboardButton(text="🔄 Kursni yangilash")],
        [KeyboardButton(text="🔙 Orqaga")],
    ], resize_keyboard=True)

def xkb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor")]],
        resize_keyboard=True
    )

FIELD_HINTS = {
    "sell_markup": ("📈 Sotish foizi (%)",       "User SO'M beradi → kripto oladi.\nFoiz OSHIRILADI (user ko'proq to'laydi).\nMasalan: 3.5"),
    "buy_markup":  ("📉 Sotib olish foizi (%)",  "User KRIPTO beradi → so'm oladi.\nFoiz KAMAYTIRILADI (user kamroq so'm oladi).\nMasalan: 3.5"),
    "commission":  ("💸 Komissiya (%)",           "Almashuv komissiyasi.\nMasalan: 1.0"),
    "min":         ("⬇️ Minimal miqdor",          "Masalan: 100000"),
    "max":         ("⬆️ Maksimal miqdor",          "Masalan: 500000000"),
}



#  /admin

@admin_config_router.message(Command("admin"))
async def admin_enter(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    db   = load_db()
    live = db.get("live_rates", {})
    last = db.get("last_rate_update", "Yangilanmagan")
    await message.answer(
        f"👨‍💼 Admin panel\n\n"
        f"📊 Live kurslar: {len(live)} ta\n"
        f"🕐 Oxirgi yangilanish: {last}",
        reply_markup=admin_kb()
    )



#  ⚙️ API FOIZLAR

def api_list_kb():
    rows = [[InlineKeyboardButton(
        text=f"💎 {cur['name']}",
        callback_data=f"AF_{cur['id']}"   # AF_ prefix — boshqa hech narsa bilan conflict yo'q
    )] for cur in CRYPTO_CURS]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def api_detail_kb(cid):
    s    = get_settings()
    db   = load_db()
    live = db.get("live_rates", {}).get(cid, {})
    sell_m = s.get(f"{cid}_sell_markup", 0.0)
    buy_m  = s.get(f"{cid}_buy_markup",  0.0)
    comm   = s.get(f"{cid}_commission",  1.0)
    mn     = s.get(f"{cid}_min", 1)
    mx     = s.get(f"{cid}_max", 100_000)
    sell_r = live.get("sell_rate", "—")
    buy_r  = live.get("buy_rate",  "—")
    s_str  = f"{sell_r:,}" if isinstance(sell_r, int) else str(sell_r)
    b_str  = f"{buy_r:,}"  if isinstance(buy_r,  int) else str(buy_r)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📈 Sotish foizi: {sell_m}%  → {s_str} so'm", callback_data=f"AFE_{cid}__sell_markup")],
        [InlineKeyboardButton(text=f"📉 Sotib olish foizi: {buy_m}%  → {b_str} so'm", callback_data=f"AFE_{cid}__buy_markup")],
        [InlineKeyboardButton(text=f"💸 Komissiya: {comm}%",    callback_data=f"AFE_{cid}__commission")],
        [InlineKeyboardButton(text=f"⬇️ Minimal: {fmt(mn)}",   callback_data=f"AFE_{cid}__min")],
        [InlineKeyboardButton(text=f"⬆️ Maksimal: {fmt(mx)}",  callback_data=f"AFE_{cid}__max")],
        [InlineKeyboardButton(text="🔙 Orqaga",                 callback_data="AF_BACK")],
    ])


@admin_config_router.message(F.text == "⚙️ API foizlar")
async def admin_api(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    await message.answer(
        "⚙️ Qaysi valyutani sozlamoqchisiz?\n\n"
        "📈 Sotish foizi — user so'm beradi, kripto qimmatroq chiqadi\n"
        "📉 Sotib olish foizi — user kripto beradi, so'm kamroq beriladi",
        reply_markup=api_list_kb()
    )

@admin_config_router.callback_query(F.data == "AF_BACK")
async def af_back(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): return
    await state.clear()
    await cb.message.edit_text("⚙️ Qaysi valyutani sozlamoqchisiz?", reply_markup=api_list_kb())
    await cb.answer()

@admin_config_router.callback_query(F.data.startswith("AF_"))
async def af_detail(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): return
    # AF_BACK yuqorida ushlandi, bu yerga faqat AF_{cid} keladi
    cid = cb.data[3:]
    cur = get_currency_by_id(cid)
    if not cur:
        await cb.answer("❌ Topilmadi", show_alert=True); return
    db   = load_db()
    live = db.get("live_rates", {}).get(cid, {})
    if live:
        text = (
            f"💎 {cur['name']} sozlamalari\n\n"
            f"🌐 API narxi: ${live.get('usd_price','—')}\n"
            f"💵 USD/UZS: {live.get('usd_uzs','—'):,.0f}\n"
            f"📊 Xom kurs: {live.get('raw_uzs','—'):,} SO'M\n"
            f"📈 Sotish kursi: {live.get('sell_rate','—'):,} SO'M\n"
            f"📉 Sotib olish kursi: {live.get('buy_rate','—'):,} SO'M\n\n"
            f"Nimani o'zgartirmoqchisiz?"
        )
    else:
        text = (
            f"💎 {cur['name']} sozlamalari\n\n"
            f"⚠️ Live kurs yo'q. '🔄 Kursni yangilash' ni bosing.\n\n"
            f"Nimani o'zgartirmoqchisiz?"
        )
    await cb.message.edit_text(text, reply_markup=api_detail_kb(cid))
    await cb.answer()

@admin_config_router.callback_query(F.data.startswith("AFE_"))
async def af_edit(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): return
    # AFE_{cid}__{field}  — __ ikki pastki chiziq ajratuvchi
    raw   = cb.data[4:]
    parts = raw.split("__", 1)
    cid, field = parts[0], parts[1]
    cur   = get_currency_by_id(cid)
    s     = get_settings()
    cur_v = s.get(f"{cid}_{field}", "0")
    label, hint = FIELD_HINTS.get(field, (field, ""))
    await state.set_state(ACS.api_edit_val)
    await state.update_data(edit_cid=cid, edit_field=field)
    await cb.message.edit_text(
        f"💎 {cur['name'] if cur else cid} — {label}\n\n"
        f"Hozirgi qiymat: {cur_v}\n\n"
        f"{hint}\n\n"
        f"Yangi qiymat kiriting:"
    )
    await cb.answer()

@admin_config_router.message(ACS.api_edit_val)
async def af_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if message.text == "❌ Bekor":
        await state.clear(); await message.answer("❌", reply_markup=admin_kb()); return
    data  = await state.get_data()
    cid   = data["edit_cid"]
    field = data["edit_field"]
    try:
        val = float(message.text.replace(",", ".").strip())
        if field in ("min", "max"): val = int(val)
    except ValueError:
        await message.answer("❌ Raqam kiriting:"); return
    s = get_settings()
    s[f"{cid}_{field}"] = val
    save_settings(s)
    await state.clear()
    note = ""
    try:
        from rates_api import update_live_rates
        await update_live_rates()
        note = "\n✅ Kurslar qayta hisoblandi."
    except Exception as e:
        note = f"\n⚠️ Kurs yangilanmadi: {e}"
    label, _ = FIELD_HINTS.get(field, (field, ""))
    await message.answer(
        f"✅ {cname(cid)} — {label}: {fmt(val)}{note}",
        reply_markup=admin_kb()
    )



#  💹 MANUAL KURSLAR

def manual_list_kb():
    manual = get_manual()
    rows   = []
    for key, info in manual.items():
        p = key.split(":")
        if len(p) == 2:
            rows.append([InlineKeyboardButton(
                text=f"💱 {cname(p[0])} ➡️ {cname(p[1])} | {info.get('rate','?')}",
                callback_data=f"MV_{key}"
            )])
    rows.append([InlineKeyboardButton(text="➕ Yangi qo'shish", callback_data="MADD")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def manual_detail_kb(key):
    info = get_manual().get(key, {})
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💱 Kurs: {info.get('rate','—')}",           callback_data=f"ME_{key}__rate")],
        [InlineKeyboardButton(text=f"⬇️ Min: {fmt(info.get('min',0))}",          callback_data=f"ME_{key}__min")],
        [InlineKeyboardButton(text=f"⬆️ Max: {fmt(info.get('max',0))}",          callback_data=f"ME_{key}__max")],
        [InlineKeyboardButton(text=f"💸 Komissiya: {info.get('commission',1)}%",  callback_data=f"ME_{key}__commission")],
        [InlineKeyboardButton(text="🗑 O'chirish",                                callback_data=f"MDEL_{key}")],
        [InlineKeyboardButton(text="🔙 Orqaga",                                   callback_data="MBACK")],
    ])

def cur_select_kb(prefix, exclude=""):
    rows = []
    row  = []
    for cur in CURRENCIES:
        if cur["id"] == exclude: continue
        row.append(InlineKeyboardButton(text=cur["name"], callback_data=f"{prefix}{cur['id']}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text="❌ Bekor", callback_data="MBACK")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@admin_config_router.message(F.text == "💹 Manual kurslar")
async def admin_manual(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    manual = get_manual()
    await message.answer(
        f"💹 Manual kurslar ({len(manual)} ta)\n"
        f"API ishlamagan juftliklar uchun.",
        reply_markup=manual_list_kb()
    )

@admin_config_router.callback_query(F.data == "MBACK")
async def mback(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): return
    await state.clear()
    manual = get_manual()
    await cb.message.edit_text(f"💹 Manual kurslar ({len(manual)} ta)", reply_markup=manual_list_kb())
    await cb.answer()

@admin_config_router.callback_query(F.data.startswith("MV_"))
async def mv_view(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    key  = cb.data[3:]
    p    = key.split(":")
    info = get_manual().get(key, {})
    await cb.message.edit_text(
        f"💱 {cname(p[0])} ➡️ {cname(p[1])}\n\n"
        f"Kurs: {info.get('rate','—')}\n"
        f"Min:  {fmt(info.get('min',0))}\n"
        f"Max:  {fmt(info.get('max',0))}\n"
        f"Komissiya: {info.get('commission',1)}%",
        reply_markup=manual_detail_kb(key)
    )
    await cb.answer()

@admin_config_router.callback_query(F.data.startswith("MDEL_"))
async def mdel(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    key    = cb.data[5:]
    manual = get_manual()
    if key in manual:
        del manual[key]; save_manual(manual)
    await cb.message.edit_text("✅ O'chirildi!", reply_markup=manual_list_kb())
    await cb.answer()

@admin_config_router.callback_query(F.data.startswith("ME_"))
async def me_field(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): return
    raw   = cb.data[3:]
    key, field = raw.split("__", 1)
    info  = get_manual().get(key, {})
    cur_v = info.get(field, "—")
    await state.set_state(ACS.man_field_val)
    await state.update_data(man_key=key, man_field=field)
    labels = {"rate": "Kurs", "min": "Minimal", "max": "Maksimal", "commission": "Komissiya (%)"}
    await cb.message.edit_text(
        f"✏️ {labels.get(field, field)}\nHozirgi: {cur_v}\n\nYangi qiymat:"
    )
    await cb.answer()

@admin_config_router.message(ACS.man_field_val)
async def me_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if message.text == "❌ Bekor":
        await state.clear(); await message.answer("❌", reply_markup=admin_kb()); return
    data  = await state.get_data()
    key, field = data["man_key"], data["man_field"]
    try:
        val = float(message.text.replace(",", "."))
        if field in ("min", "max"): val = int(val)
    except:
        await message.answer("❌ Raqam kiriting:"); return
    manual = get_manual()
    if key not in manual: manual[key] = {}
    manual[key][field] = val
    save_manual(manual)
    await state.clear()
    await message.answer(f"✅ Yangilandi: {fmt(val)}", reply_markup=admin_kb())

@admin_config_router.callback_query(F.data == "MADD")
async def madd(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): return
    await state.update_data(man_step="from")
    await cb.message.edit_text("➕ 1-valyuta (FROM):", reply_markup=cur_select_kb("MFROM_"))
    await cb.answer()

@admin_config_router.callback_query(F.data.startswith("MFROM_"))
async def mfrom(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): return
    fid = cb.data[6:]
    await state.update_data(man_from_id=fid)
    await cb.message.edit_text(
        f"✅ FROM: {cname(fid)}\n\n2-valyuta (TO):",
        reply_markup=cur_select_kb("MTO_", exclude=fid)
    )
    await cb.answer()

@admin_config_router.callback_query(F.data.startswith("MTO_"))
async def mto(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): return
    tid  = cb.data[4:]
    data = await state.get_data()
    await state.update_data(man_to_id=tid)
    await state.set_state(ACS.man_rate)
    await cb.message.edit_text(
        f"✅ {cname(data['man_from_id'])} ➡️ {cname(tid)}\n\n"
        f"💱 Kursni kiriting (1 {cname(data['man_from_id'])} = ? {cname(tid)}):"
    )
    await cb.answer()

@admin_config_router.message(ACS.man_rate)
async def mrate(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if message.text == "❌ Bekor":
        await state.clear(); await message.answer("❌", reply_markup=admin_kb()); return
    try: v = float(message.text.replace(",", "."))
    except: await message.answer("❌ Raqam:"); return
    await state.update_data(man_rate_v=v)
    await state.set_state(ACS.man_min)
    await message.answer(f"✅ Kurs: {v}\n\n⬇️ Minimal miqdor:")

@admin_config_router.message(ACS.man_min)
async def mmin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try: v = int(float(message.text.replace(",", "")))
    except: await message.answer("❌ Raqam:"); return
    await state.update_data(man_min_v=v)
    await state.set_state(ACS.man_max)
    await message.answer(f"✅ Min: {v:,}\n\n⬆️ Maksimal miqdor:")

@admin_config_router.message(ACS.man_max)
async def mmax(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try: v = int(float(message.text.replace(",", "")))
    except: await message.answer("❌ Raqam:"); return
    await state.update_data(man_max_v=v)
    await state.set_state(ACS.man_comm)
    await message.answer(f"✅ Max: {v:,}\n\n💸 Komissiya (%):")

@admin_config_router.message(ACS.man_comm)
async def mcomm(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try: v = float(message.text.replace(",", "."))
    except: await message.answer("❌ Raqam:"); return
    data   = await state.get_data()
    key    = f"{data['man_from_id']}:{data['man_to_id']}"
    manual = get_manual()
    manual[key] = {
        "rate": data["man_rate_v"], "min": data["man_min_v"],
        "max": data["man_max_v"],   "commission": v,
    }
    save_manual(manual)
    await state.clear()
    await message.answer(
        f"✅ Qo'shildi!\n"
        f"💱 {cname(data['man_from_id'])} ➡️ {cname(data['man_to_id'])}\n"
        f"Kurs: {data['man_rate_v']} | Min: {fmt(data['man_min_v'])} | Max: {fmt(data['man_max_v'])} | Komissiya: {v}%",
        reply_markup=admin_kb()
    )



#  💳 TO'LOV KARTALARI

def cards_kb():
    cards = get_cards()
    rows  = []
    for cur in CURRENCIES:
        num  = cards.get(cur["id"], "—")
        icon = "💳" if cur["type"] == "card" else "📲"
        rows.append([InlineKeyboardButton(
            text=f"{icon} {cur['name']}: {num}",
            callback_data=f"CARD_{cur['id']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@admin_config_router.message(F.text == "💳 To'lov kartalari")
async def admin_cards(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    await message.answer("💳 To'lov kartalari / Walletlar:", reply_markup=cards_kb())

@admin_config_router.callback_query(F.data.startswith("CARD_"))
async def card_edit(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): return
    cid   = cb.data[5:]
    cur   = get_currency_by_id(cid)
    cur_v = get_cards().get(cid, "—")
    t     = "karta raqami" if cur and cur["type"] == "card" else "wallet manzili"
    await state.set_state(ACS.card_val)
    await state.update_data(card_cid=cid)
    await cb.message.edit_text(
        f"{'💳' if cur and cur['type']=='card' else '📲'} {cur['name'] if cur else cid}\n\n"
        f"Hozirgi: <code>{cur_v}</code>\n\n"
        f"Yangi {t} kiriting:",
        parse_mode="HTML"
    )
    await cb.answer()

@admin_config_router.message(ACS.card_val)
async def card_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if message.text == "❌ Bekor":
        await state.clear(); await message.answer("❌", reply_markup=admin_kb()); return
    data  = await state.get_data()
    cid   = data["card_cid"]
    cards = get_cards()
    cards[cid] = message.text.strip()
    save_cards(cards)
    await state.clear()
    cur = get_currency_by_id(cid)
    await message.answer(
        f"✅ {cur['name'] if cur else cid} yangilandi!\n<code>{message.text.strip()}</code>",
        reply_markup=admin_kb(), parse_mode="HTML"
    )



#  🔄 KURSNI YANGILASH

@admin_config_router.message(F.text == "🔄 Kursni yangilash")
async def admin_refresh(message: Message):
    if not is_admin(message.from_user.id): return
    msg = await message.answer("⏳ Yangilanmoqda...")
    try:
        from rates_api import update_live_rates, get_rates_text
        live = await update_live_rates()
        text = get_rates_text("uz")
        await msg.edit_text(f"✅ {len(live)} ta kurs yangilandi!\n\n{text}")
    except Exception as e:
        await msg.edit_text(f"❌ Xato: {e}")



#  📦 BUYURTMALAR

STATUS = {
    "pending_payment": "⏳ Kutilmoqda",
    "receipt_sent":    "🧾 Chek yuborilgan",
    "completed":       "✅ Yakunlangan",
    "cancelled":       "❌ Bekor",
}

def orders_kb():
    orders  = get_orders()
    pending = sum(1 for o in orders.values() if o.get("status") in ("pending_payment","receipt_sent"))
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⏳ Kutilayotgan ({pending})", callback_data="ORD_f_pending")],
        [InlineKeyboardButton(text="🧾 Chek yuborilgan",           callback_data="ORD_f_receipt")],
        [InlineKeyboardButton(text="✅ Yakunlangan",               callback_data="ORD_f_done")],
        [InlineKeyboardButton(text="❌ Bekor qilingan",            callback_data="ORD_f_cancelled")],
        [InlineKeyboardButton(text="📋 Barchasi",                  callback_data="ORD_f_all")],
    ])

def ord_action_kb(oid, status):
    rows = []
    if status in ("pending_payment","receipt_sent"):
        rows.append([InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"OCONF_{oid}")])
        rows.append([InlineKeyboardButton(text="❌ Rad etish",  callback_data=f"OREJ_{oid}")])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="ORD_BACK")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@admin_config_router.message(F.text == "📦 Buyurtmalar")
async def admin_orders(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    orders = get_orders()
    p = sum(1 for o in orders.values() if o.get("status") in ("pending_payment","receipt_sent"))
    await message.answer(f"📦 Buyurtmalar\nJami: {len(orders)} | ⏳: {p}", reply_markup=orders_kb())

@admin_config_router.callback_query(F.data == "ORD_BACK")
async def ord_back(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    orders = get_orders()
    p = sum(1 for o in orders.values() if o.get("status") in ("pending_payment","receipt_sent"))
    await cb.message.edit_text(f"📦 Buyurtmalar\nJami: {len(orders)} | ⏳: {p}", reply_markup=orders_kb())
    await cb.answer()

@admin_config_router.callback_query(F.data.startswith("ORD_f_"))
async def ord_list(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    filt = cb.data[6:]
    fmap = {
        "pending":   ["pending_payment"],
        "receipt":   ["receipt_sent"],
        "done":      ["completed"],
        "cancelled": ["cancelled"],
        "all":       list(STATUS.keys()),
    }
    allowed  = fmap.get(filt, [])
    filtered = sorted(
        [o for o in get_orders().values() if o.get("status") in allowed],
        key=lambda x: x.get("order_id", 0), reverse=True
    )
    if not filtered:
        await cb.answer("📭 Yo'q", show_alert=True); return
    rows = []
    for o in filtered[:15]:
        icon = {"pending_payment":"⏳","receipt_sent":"🧾","completed":"✅","cancelled":"❌"}.get(o.get("status"),"❓")
        rows.append([InlineKeyboardButton(
            text=f"{icon} #{o['order_id']} | {o.get('from_name','?')}→{o.get('to_name','?')} | {fmt(o.get('send_amount',0))}",
            callback_data=f"ORD_v_{o['order_id']}"
        )])
    rows.append([InlineKeyboardButton(text="🔙", callback_data="ORD_BACK")])
    await cb.message.edit_text(f"📋 {len(filtered)} ta:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await cb.answer()

@admin_config_router.callback_query(F.data.startswith("ORD_v_"))
async def ord_view(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    oid = int(cb.data[6:])
    o   = get_orders().get(str(oid))
    if not o: await cb.answer("❌", show_alert=True); return
    text = (
        f"📦 Buyurtma #{o['order_id']}\n"
        f"📅 {o.get('created_at','—')}\n"
        f"🔖 {STATUS.get(o.get('status',''),'—')}\n\n"
        f"👤 {o.get('full_name','—')} (@{o.get('username','—')})\n"
        f"🆔 {o.get('user_id','—')}\n\n"
        f"🔄 {o.get('from_name','?')} ➡️ {o.get('to_name','?')}\n"
        f"⬆️ Beradi: {fmt(o.get('send_amount',0))} {o.get('from_name','')}\n"
        f"⬇️ Oladi: {fmt(o.get('recv_amount', o.get('receive_amount',0)))} {o.get('to_name','')}\n\n"
        f"💳 {o.get('from_name','')}: <code>{o.get('sender_card','—')}</code>\n"
        f"💳 {o.get('to_name','')}: <code>{o.get('receiver_card','—')}</code>"
    )
    await cb.message.edit_text(text, reply_markup=ord_action_kb(oid, o.get("status","")), parse_mode="HTML")
    await cb.answer()

@admin_config_router.callback_query(F.data.startswith("OCONF_"))
async def oconf(cb: CallbackQuery, bot: Bot):
    if not is_admin(cb.from_user.id): return
    oid = int(cb.data[6:])
    set_order_status(oid, "completed")
    uid = get_orders().get(str(oid), {}).get("user_id")
    try: await bot.send_message(uid, f"✅ Buyurtma #{oid} tasdiqlandi!\n\nPulingiz tez orada o'tkaziladi. Rahmat!")
    except: pass
    await cb.message.edit_text(f"✅ #{oid} tasdiqlandi!")
    await cb.answer("✅")

@admin_config_router.callback_query(F.data.startswith("OREJ_"))
async def orej(cb: CallbackQuery, bot: Bot):
    if not is_admin(cb.from_user.id): return
    oid = int(cb.data[5:])
    set_order_status(oid, "cancelled")
    uid = get_orders().get(str(oid), {}).get("user_id")
    try: await bot.send_message(uid, f"❌ Buyurtma #{oid} rad etildi.\n\nSavollar uchun admin bilan bog'laning.")
    except: pass
    await cb.message.edit_text(f"❌ #{oid} rad etildi.")
    await cb.answer("❌")



#  📢 KANALLAR

@admin_config_router.message(F.text == "📢 Kanallar")
async def admin_channels(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    chs = get_channels()
    text = "📢 Kanallar:\n\n" + "\n".join(
        f"{i}. {ch['channel_name']} | {ch['channel_link']} | {ch['channel_id']}"
        for i,ch in enumerate(chs,1)
    ) if chs else "📭 Kanallar yo'q."
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Qo'shish", callback_data="CH_ADD")],
        [InlineKeyboardButton(text="➖ O'chirish", callback_data="CH_DEL")],
    ]))

@admin_config_router.callback_query(F.data == "CH_ADD")
async def ch_add(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): return
    await state.set_state(ACS.ch_id)
    await cb.message.edit_text("Kanal ID kiriting (masalan: -1001234567890):")
    await cb.answer()

@admin_config_router.message(ACS.ch_id)
async def ch_id_val(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try:
        cid = int(message.text.strip())
        await state.update_data(ch_id=cid)
        await state.set_state(ACS.ch_link)
        await message.answer("Kanal havolasi (https://t.me/...):")
    except: await message.answer("❌ Son bo'lishi kerak:")

@admin_config_router.message(ACS.ch_link)
async def ch_link_val(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.update_data(ch_link=message.text.strip())
    await state.set_state(ACS.ch_name)
    await message.answer("Kanal nomi:")

@admin_config_router.message(ACS.ch_name)
async def ch_name_val(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    ok   = add_channel(data["ch_id"], data["ch_link"], message.text.strip())
    await state.clear()
    await message.answer(
        f"✅ {message.text.strip()} qo'shildi!" if ok else "❌ Allaqachon mavjud!",
        reply_markup=admin_kb()
    )

@admin_config_router.callback_query(F.data == "CH_DEL")
async def ch_del_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): return
    chs = get_channels()
    if not chs: await cb.answer("📭 Yo'q", show_alert=True); return
    text = "O'chirish uchun kanal ID ni kiriting:\n\n" + "\n".join(
        f"• {ch['channel_name']} → {ch['channel_id']}" for ch in chs
    )
    await state.set_state(ACS.ch_del)
    await cb.message.edit_text(text)
    await cb.answer()

@admin_config_router.message(ACS.ch_del)
async def ch_del_val(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try:
        ok = remove_channel(int(message.text.strip()))
        await state.clear()
        await message.answer("✅ O'chirildi!" if ok else "❌ Topilmadi!", reply_markup=admin_kb())
    except: await message.answer("❌ Son bo'lishi kerak:")



#  👥 FOYDALANUVCHILAR

@admin_config_router.message(F.text == "👥 Foydalanuvchilar")
async def admin_users(message: Message):
    if not is_admin(message.from_user.id): return
    await message.answer(f"👥 Ro'yxatdan o'tganlar: {len(get_all_users())} ta")



#  📨 BROADCAST

@admin_config_router.message(F.text == "📨 Broadcast")
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(ACS.broadcast)
    await message.answer("Xabarni kiriting:", reply_markup=xkb())

@admin_config_router.message(ACS.broadcast)
async def broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id): return
    if message.text == "❌ Bekor":
        await state.clear(); await message.answer("❌", reply_markup=admin_kb()); return
    users = get_all_users()
    ok = 0
    for uid in users:
        try: await bot.send_message(int(uid), message.text); ok += 1
        except: pass
    await state.clear()
    await message.answer(f"✅ {ok}/{len(users)} ta yuborildi!", reply_markup=admin_kb())

@admin_config_router.message(F.text == "🔙 Orqaga")
async def admin_back(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    from keyboards import main_menu_keyboard
    from database import get_user
    user = get_user(message.from_user.id)
    lang = user.get("lang", "uz") if user else "uz"
    await message.answer("🏠 Asosiy menyu", reply_markup=main_menu_keyboard(lang))