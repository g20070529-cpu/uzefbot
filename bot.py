import asyncio
import sqlite3
import re
import html
import os
from aiogram import Bot, Dispatcher, F, types, BaseMiddleware
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ================= SOZLAMALAR =================
TOKEN = os.getenv("TOKEN")
CHANNEL = "@UZEF_SHOP"
ADMIN_ID = 7252768667
MAIN_ADMINS = [7252768667, 7494065582]
BOT_USERNAME = "@Uzefshop_bot"
DEFAULT_BUY_IMAGE = "AAMCAgADGQEDIqkmahJ_uvW5vHCRyHScqLndDEp_azgAAj-dAALIzJhI8jsGqtT6uNoBAAdtAAM7BA"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ================= MA'LUMOTLAR BAZASI =================
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, type TEXT, photo_id TEXT,
        text_content TEXT, message_id INTEGER, price TEXT,
        discount_count INTEGER DEFAULT 0, status TEXT DEFAULT 'pending'
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS garant_admins (
        username TEXT PRIMARY KEY
    )''')
    # Boshlang'ich garant adminlar
    for u in ["uzefowner", "SA1DOV707", "Makhmudov_og"]:
        cur.execute("INSERT OR IGNORE INTO garant_admins (username) VALUES (?)", (u,))
    conn.commit()
    conn.close()

# ================= GARANT ADMINLAR =================
def get_garant_admins():
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("SELECT username FROM garant_admins ORDER BY rowid")
    rows = cur.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_garant_text():
    admins = get_garant_admins()
    admin_list = "\n".join([f"👤@{u}" for u in admins])
    return (
        f"<blockquote>♻️OLDI SOTDI GARANT ADMINLAR\n"
        f"Adminsiz savdo 99% aldov bilan tugaydi garand adminsiz savdo qilmang ‼️\n\n"
        f"Garand admin🧑‍💻:\n{admin_list}</blockquote>"
    )

def add_garant_admin(username: str):
    username = username.replace("@", "").strip()
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO garant_admins (username) VALUES (?)", (username,))
    conn.commit()
    conn.close()

def remove_garant_admin(username: str):
    username = username.replace("@", "").strip()
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM garant_admins WHERE username = ?", (username,))
    conn.commit()
    conn.close()

# ================= OLISH ELONI RASMI =================
def get_buy_image():
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = 'buy_image'")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else DEFAULT_BUY_IMAGE

# ================= HOLATLAR =================
class SellAd(StatesGroup):
    image, gc, obmen, price, izoh, receipt = State(), State(), State(), State(), State(), State()

class BuyAd(StatesGroup):
    budget, gc, malumot, receipt = State(), State(), State(), State()

class MyAds(StatesGroup):
    new_price = State()

# ================= KLAVIATURALAR =================
def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Elon berish")],
        [KeyboardButton(text="Elon narxlari"), KeyboardButton(text="Elonlarim")],
        [KeyboardButton(text="Adminlar")]
    ], resize_keyboard=True)

def ad_types_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Sotish eloni"), KeyboardButton(text="Olish eloni")],
        [KeyboardButton(text="⬅️ Ortga")]
    ], resize_keyboard=True)

def yes_no_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅"), KeyboardButton(text="❎")]], resize_keyboard=True)

def only_exchange_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Faqat obmen")]], resize_keyboard=True)

def payment_inline_btn():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="To'lov qildim ✅", callback_data="paid_receipt")]])

def admin_approve_menu(ad_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{ad_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{ad_id}")
    ]])

def my_ads_menu(ad_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Narxni tushirish", callback_data=f"discount_{ad_id}")],
        [InlineKeyboardButton(text="🤝 Sotildi", callback_data=f"sold_{ad_id}")]
    ])

def sub_inline_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL.replace('@', '')}")],
        [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")]
    ])

def has_links(text: str) -> bool:
    return bool(text and re.search(r'(@|t\.me|http|www)', text, re.IGNORECASE))

# ================= TIMEOUT MIDDLEWARE =================
user_tasks = {}

async def cancel_state_after_timeout(user_id, state, bot_instance):
    try:
        await asyncio.sleep(300)
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()
            await bot_instance.send_message(
                chat_id=user_id,
                text="⏳ Vaqt tugadi! 5 daqiqa davomida ma'lumot kiritmaganingiz uchun amaliyot bekor qilindi.",
                reply_markup=main_menu()
            )
    except asyncio.CancelledError:
        pass

class TimeoutMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: types.Message, data: dict):
        user_id = event.from_user.id
        state: FSMContext = data.get("state")
        bot_instance: Bot = data.get("bot")
        if user_id in user_tasks:
            user_tasks[user_id].cancel()
        result = await handler(event, data)
        current_state = await state.get_state()
        if current_state is not None:
            task = asyncio.create_task(cancel_state_after_timeout(user_id, state, bot_instance))
            user_tasks[user_id] = task
        elif user_id in user_tasks:
            del user_tasks[user_id]
        return result

dp.message.middleware(TimeoutMiddleware())

async def is_subscribed(user_id: int) -> bool:
    if user_id in MAIN_ADMINS: return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL, user_id=user_id)
        return member.status not in ["left", "kicked"]
    except Exception:
        return False

# ================= ASOSIY HANDLERLAR =================
@dp.message(CommandStart())
@dp.message(Command("restart"))
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    if await is_subscribed(message.from_user.id):
        await message.answer("Assalomu alaykum! E'lon berish botiga xush kelibsiz.", reply_markup=main_menu())
    else:
        await message.answer("Hurmatli foydalanuvchi!\n\nBotdan foydalanish uchun kanalimizga obuna bo'ling.", reply_markup=sub_inline_menu())

@dp.callback_query(F.data == "check_sub")
async def check_sub_handler(call: types.CallbackQuery):
    if await is_subscribed(call.from_user.id):
        try: await call.message.delete()
        except Exception: pass
        await call.message.answer("✅ Obuna tasdiqlandi! Bosh menyudasiz.", reply_markup=main_menu())
    else:
        await call.answer("❌ Hali kanalga obuna bo'lmadingiz!", show_alert=True)

@dp.message(F.text == "⬅️ Ortga")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Bosh sahifaga qaytdingiz.", reply_markup=main_menu())

@dp.message(F.text == "Adminlar")
async def show_admins(message: types.Message):
    await message.answer(get_garant_text())

@dp.message(F.text == "Elon narxlari")
async def elon_narxlari(message: types.Message):
    await message.answer("🛍Akkauntlarga e'lon berish narxlari:\nHar qanaqa akkaunt narxi 2000 so'm\n\n❗️Akkount olaman deb reklama berishingiz ham mumkin!")

@dp.message(F.text == "Elon berish")
async def elon_berish(message: types.Message, state: FSMContext):
    await state.clear()
    if await is_subscribed(message.from_user.id):
        await message.answer("Qanday turdagi elon joylamoqchisiz?", reply_markup=ad_types_menu())
    else:
        await message.answer("E'lon berish uchun avval kanalimizga obuna bo'ling!", reply_markup=sub_inline_menu())

# ================= ADMIN BUYRUQLARI =================
@dp.message(Command("addadmin"))
async def cmd_add_admin(message: types.Message):
    if message.from_user.id not in MAIN_ADMINS:
        return await message.answer("❌ Bu buyruq faqat bosh adminlar uchun!")
    parts = message.text.split()
    if len(parts) != 2:
        return await message.answer("❌ To'g'ri format:\n/addadmin @username")
    username = parts[1].replace("@", "")
    add_garant_admin(username)
    await message.answer(f"✅ @{username} garant admin ro'yxatiga qo'shildi!")

@dp.message(Command("banadmin"))
async def cmd_ban_admin(message: types.Message):
    if message.from_user.id not in MAIN_ADMINS:
        return await message.answer("❌ Bu buyruq faqat bosh adminlar uchun!")
    parts = message.text.split()
    if len(parts) != 2:
        return await message.answer("❌ To'g'ri format:\n/banadmin @username")
    username = parts[1].replace("@", "")
    remove_garant_admin(username)
    await message.answer(f"✅ @{username} garant admin ro'yxatidan olib tashlandi!")

@dp.message(Command("banrasm"))
async def cmd_ban_rasm(message: types.Message):
    if message.from_user.id not in MAIN_ADMINS:
        return await message.answer("❌ Bu buyruq faqat bosh adminlar uchun!")
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM settings WHERE key = 'buy_image'")
    conn.commit()
    conn.close()
    await message.answer("✅ Olish eloni rasmi o'chirildi!")

# ================= RASM QOYISH (faqat state yo'q vaqtda) =================
@dp.message(F.photo, StateFilter(None))
async def set_buy_image(message: types.Message):
    if message.from_user.id not in MAIN_ADMINS: return
    if message.caption and message.caption.lower() == "/setrasm":
        file_id = message.photo[-1].file_id
        conn = sqlite3.connect("bot_database.db")
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('buy_image', ?)", (file_id,))
        conn.commit()
        conn.close()
        await message.answer("✅ Olish eloni rasmi muvaffaqiyatli saqlandi!")

# ================= SOTISH ELONI =================
@dp.message(F.text == "Sotish eloni")
async def start_sell_ad(message: types.Message, state: FSMContext):
    if not await is_subscribed(message.from_user.id): return
    await message.answer("Shu ko'rinishda asosiy tarkib rasmini yuboring :", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(SellAd.image)

@dp.message(SellAd.image, F.photo)
async def sell_image(message: types.Message, state: FSMContext):
    if message.media_group_id:
        return await message.answer("❌ Iltimos, bitta asosiy rasmni yuboring!")
    await state.update_data(photo_id=message.photo[-1].file_id)
    await message.answer("Qabul qilindi, akkountingizga Google yoki Game Center ulanganmi? ✅ ❎", reply_markup=yes_no_menu())
    await state.set_state(SellAd.gc)

@dp.message(SellAd.image)
async def sell_image_invalid(message: types.Message):
    await message.answer("❌ Iltimos, faqat rasm yuboring!")

@dp.message(SellAd.gc, F.text.in_(["✅", "❎"]))
async def sell_gc(message: types.Message, state: FSMContext):
    await state.update_data(gc="Ulangan" if message.text == "✅" else "Toza")
    await message.answer("Qabul qilindi, ushbu akkountingizga obmen korasizmi? ✅ ❎", reply_markup=yes_no_menu())
    await state.set_state(SellAd.obmen)

@dp.message(SellAd.obmen, F.text.in_(["✅", "❎"]))
async def sell_obmen(message: types.Message, state: FSMContext):
    await state.update_data(obmen="Bor" if message.text == "✅" else "Yo'q")
    await message.answer("Akkountingiz sotiladimi yoki obmen uchunmi?\n\nNarxni kiritish (Masalan: 100000)", reply_markup=only_exchange_menu())
    await state.set_state(SellAd.price)

@dp.message(SellAd.price)
async def sell_price(message: types.Message, state: FSMContext):
    if not message.text: return await message.answer("❌ Iltimos, narxni yozing!")
    text = message.text
    if has_links(text): return await message.answer("Ogohlantirish! Reklama taqiqlangan.")
    if text != "Faqat obmen" and not text.replace(' ', '').isdigit():
        return await message.answer("❌ Iltimos, narxni faqat raqamlarda kiriting:")
    await state.update_data(price=html.escape(text))
    await message.answer("Akkountga qo'shimcha izoh yozishingiz mumkin", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(SellAd.izoh)

@dp.message(SellAd.izoh)
async def sell_izoh(message: types.Message, state: FSMContext):
    if not message.text or message.text.isdigit() or has_links(message.text):
        return await message.answer("❌ Iltimos, izohni to'g'ri yozing!")
    data = await state.get_data()
    price = data['price']
    tags = "#SOTILMAYDI #FAQAT_OBMEN" if price.lower() == "faqat obmen" else "#SOTILADI"
    narx_text = "#OBMEN_UCHUN" if price.lower() == "faqat obmen" else f"{price}"
    ad_text = (
        f"{tags}\n\n💴 Narx: {narx_text}\n♻️ Obmen ko'rish: {data['obmen']}\n⚠️ Google & Game Center: {data['gc']}\n"
        f"☎️ Murojaat: <a href='tg://user?id={message.from_user.id}'>{html.escape(message.from_user.first_name)}</a>\n\n"
        f"📋 Qo'shilgan ma'lumot:\n<blockquote>{html.escape(message.text)}</blockquote>\n\n"
        f"{get_garant_text()}\n\nReklama berish uchun 📣:\n{BOT_USERNAME} ⚜️"
    )
    await state.update_data(final_text=ad_text, ad_type="sell")
    if message.from_user.id in MAIN_ADMINS:
        await publish_ad(message.from_user.id, "sell", data['photo_id'], ad_text, price)
        await message.answer("Admin ekani tasdiqlandi. E'lon joylandi!", reply_markup=main_menu())
        return await state.clear()
    await message.answer_photo(photo=data['photo_id'], caption=ad_text)
    await message.answer("✅ E'lon yuborishga tayyor!\n\n💰 Xizmat narxi: 2 000 so'm\nAdmin karta raqami ;\n9860166654505204\nSunnatov Shukurullo\n\n⏳ 5 daqiqa ichida to'lov qiling.", reply_markup=payment_inline_btn())
    await state.set_state(SellAd.receipt)

# ================= OLISH ELONI =================
@dp.message(F.text == "Olish eloni")
async def start_buy_ad(message: types.Message, state: FSMContext):
    if not await is_subscribed(message.from_user.id): return
    await message.answer("💵 Elon uchun budjetingizni yuboring:\n\nMasalan: 500000", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(BuyAd.budget)

@dp.message(BuyAd.budget)
async def buy_budget(message: types.Message, state: FSMContext):
    if not message.text or not message.text.replace(' ', '').isdigit() or has_links(message.text):
        return await message.answer("❌ Iltimos, budjetni faqat raqamlarda kiriting:")
    await state.update_data(budget=html.escape(message.text))
    await message.answer("🔐 Qabul qilindi, Google yoki Game Center akkount ko'rasizmi? ✅ ❎", reply_markup=yes_no_menu())
    await state.set_state(BuyAd.gc)

@dp.message(BuyAd.gc, F.text.in_(["✅", "❎"]))
async def buy_gc(message: types.Message, state: FSMContext):
    await state.update_data(tag="#OLINADI #FAQAT_TOZA" if message.text == "❎" else "#OLINADI")
    await message.answer("📝 Qanday akkaunt kerakligini to'liq yozing:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(BuyAd.malumot)

@dp.message(BuyAd.malumot)
async def buy_malumot(message: types.Message, state: FSMContext):
    if not message.text or message.text.isdigit() or has_links(message.text):
        return await message.answer("❌ Iltimos, ma'lumotni to'g'ri yozing!")
    data = await state.get_data()
    buy_image = get_buy_image()
    ad_text = (
        f"{data['tag']}\n\n💴 BUDJET: {data['budget']}\n📋 Ma'lumot:\n<blockquote>{html.escape(message.text)}</blockquote>\n"
        f"☎️ Murojaat: <a href='tg://user?id={message.from_user.id}'>{html.escape(message.from_user.first_name)}</a>\n\n"
        f"{get_garant_text()}\n\nReklama berish uchun 📣:\n{BOT_USERNAME} ⚜️"
    )
    await state.update_data(final_text=ad_text, price=data['budget'], ad_type="buy", photo_id=buy_image)
    if message.from_user.id in MAIN_ADMINS:
        await publish_ad(message.from_user.id, "buy", buy_image, ad_text, data['budget'])
        await message.answer("Admin ekani tasdiqlandi. E'lon joylandi!", reply_markup=main_menu())
        return await state.clear()
    await message.answer_photo(photo=buy_image, caption=ad_text)
    await message.answer("✅ E'lon yuborishga tayyor!\n\n💰 Xizmat narxi: 2 000 so'm\nAdmin karta raqami ;\n9860166654505204\nSunnatov Shukurullo\n\n⏳ 5 daqiqa ichida to'lov qiling.", reply_markup=payment_inline_btn())
    await state.set_state(BuyAd.receipt)

# ================= TO'LOV =================
@dp.callback_query(F.data == "paid_receipt", StateFilter(SellAd.receipt, BuyAd.receipt))
async def ask_receipt(call: types.CallbackQuery):
    await call.message.answer("To'lov chekini rasm ko'rinishida yuboring:")
    await call.answer()

@dp.message(StateFilter(SellAd.receipt, BuyAd.receipt), F.photo)
async def receive_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO ads (user_id, type, photo_id, text_content, price, status) VALUES (?, ?, ?, ?, ?, 'pending')",
                (message.from_user.id, data.get("ad_type", "sell"), data.get("photo_id", ""), data['final_text'], data['price']))
    ad_id = cur.lastrowid
    conn.commit()
    conn.close()
    admin_text = f"Yangi to'lov cheki!\nUser ID: {message.from_user.id}\nUsername: @{message.from_user.username}\nE'lon turi: {data.get('ad_type', 'sell')}"
    await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=admin_approve_menu(ad_id))
    await message.answer("Chek adminga yuborildi. Tasdiqlangach e'lon kanalga joylanadi.", reply_markup=main_menu())
    await state.clear()

@dp.message(StateFilter(SellAd.receipt, BuyAd.receipt))
async def invalid_receipt(message: types.Message):
    await message.answer("❌ Iltimos, to'lov chekini faqat rasm qilib yuboring!")

@dp.callback_query(F.data.startswith("approve_"))
async def admin_approve(call: types.CallbackQuery):
    ad_id = int(call.data.split("_")[1])
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("SELECT user_id, type, photo_id, text_content, price FROM ads WHERE id = ?", (ad_id,))
    ad_data = cur.fetchone()
    if ad_data:
        msg_id = await publish_ad(ad_data[0], ad_data[1], ad_data[2], ad_data[3], ad_data[4])
        cur.execute("UPDATE ads SET status = 'active', message_id = ? WHERE id = ?", (msg_id, ad_id))
        try: await bot.send_message(ad_data[0], "✅ To'lovingiz tasdiqlandi va e'lon kanalga joylandi!")
        except Exception: pass
        await call.message.edit_caption(caption=call.message.caption + "\n\n✅ TASDIQLANDI")
    conn.commit()
    conn.close()
    await call.answer()

@dp.callback_query(F.data.startswith("reject_"))
async def admin_reject(call: types.CallbackQuery):
    ad_id = int(call.data.split("_")[1])
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM ads WHERE id = ?", (ad_id,))
    ad_data = cur.fetchone()
    if ad_data:
        try: await bot.send_message(ad_data[0], "❌ To'lovingiz tasdiqlanmadi.")
        except Exception: pass
        cur.execute("UPDATE ads SET status = 'rejected' WHERE id = ?", (ad_id,))
    conn.commit()
    conn.close()
    await call.message.edit_caption(caption=call.message.caption + "\n\n❌ RAD ETILDI")
    await call.answer()

async def publish_ad(user_id, ad_type, photo_id, text_content, price) -> int:
    if photo_id:
        msg = await bot.send_photo(chat_id=CHANNEL, photo=photo_id, caption=text_content)
    else:
        msg = await bot.send_message(chat_id=CHANNEL, text=text_content)
    if user_id in MAIN_ADMINS:
        conn = sqlite3.connect("bot_database.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO ads (user_id, type, photo_id, text_content, message_id, price, status) VALUES (?, ?, ?, ?, ?, ?, 'active')",
                    (user_id, ad_type, photo_id, text_content, msg.message_id, price))
        conn.commit()
        conn.close()
    return msg.message_id

# ================= ELONLARIM =================
@dp.message(F.text == "Elonlarim")
async def my_ads(message: types.Message):
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("SELECT id, message_id, price FROM ads WHERE user_id = ? AND status = 'active'", (message.from_user.id,))
    active_ads = cur.fetchall()
    conn.close()
    if not active_ads:
        return await message.answer("Sizda faol e'lonlar mavjud emas.")
    for ad_id, msg_id, price in active_ads:
        await message.answer(f"Reklama: https://t.me/{CHANNEL.replace('@', '')}/{msg_id}\nJoriy narx: {price}", reply_markup=my_ads_menu(ad_id), disable_web_page_preview=True)

@dp.callback_query(F.data.startswith("discount_"))
async def ask_discount(call: types.CallbackQuery, state: FSMContext):
    ad_id = int(call.data.split("_")[1])
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("SELECT discount_count FROM ads WHERE id = ?", (ad_id,))
    res = cur.fetchone()
    conn.close()
    if res and res[0] >= 2:
        return await call.answer("Narxni maksimal 2 marta tushirgansiz!", show_alert=True)
    await state.update_data(ad_id=ad_id)
    await call.message.answer("Yangi narxni kiriting:")
    await state.set_state(MyAds.new_price)

@dp.message(MyAds.new_price)
async def process_discount(message: types.Message, state: FSMContext):
    if not message.text or not message.text.replace(' ', '').isdigit() or has_links(message.text):
        return await message.answer("❌ Iltimos, faqat raqam kiriting:")
    new_price = html.escape(message.text)
    data = await state.get_data()
    ad_id = data['ad_id']
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("SELECT message_id, price FROM ads WHERE id = ?", (ad_id,))
    ad_data = cur.fetchone()
    if ad_data:
        try:
            await bot.send_message(chat_id=CHANNEL, text=f"#FAST Yangi narxi: <s>{ad_data[1]}</s>  {new_price}", reply_to_message_id=ad_data[0])
            cur.execute("UPDATE ads SET price = ?, discount_count = discount_count + 1 WHERE id = ?", (new_price, ad_id))
            conn.commit()
            await message.answer("Narx muvaffaqiyatli tushirildi!", reply_markup=main_menu())
        except Exception as e:
            await message.answer(f"Xatolik: {e}")
    conn.close()
    await state.clear()

@dp.callback_query(F.data.startswith("sold_"))
async def mark_sold(call: types.CallbackQuery):
    ad_id = int(call.data.split("_")[1])
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("SELECT message_id FROM ads WHERE id = ?", (ad_id,))
    ad_data = cur.fetchone()
    if ad_data:
        try:
            await bot.send_message(chat_id=CHANNEL, text="#SOTILDI", reply_to_message_id=ad_data[0])
            cur.execute("UPDATE ads SET status = 'sold' WHERE id = ?", (ad_id,))
            conn.commit()
            await call.message.edit_text(call.message.text + "\n\n✅ SOTILDI")
        except Exception as e:
            await call.answer(f"Xatolik: {e}", show_alert=True)
    conn.close()

# ================= MAIN =================
async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    print("Railway'da bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
