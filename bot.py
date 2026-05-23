import asyncio
import sqlite3
import re
import html
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# --- SOZLAMALAR ---
TOKEN = "8852882084:AAH7LTSmts20iLk6r25xvW0j1XkdOxV3ZMw"
CHANNEL = "@UZEF_SHOP"
ADMIN_ID = 7252768667
BOT_USERNAME = "@Uzefshop_bot"

# Render uchun oddiy bot (Proxy keraksiz)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASI (SQLite) ---
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            photo_id TEXT,
            text_content TEXT,
            message_id INTEGER,
            price TEXT,
            discount_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()
    conn.close()

# --- HOLATLAR (FSM) ---
class SellAd(StatesGroup):
    image = State()
    gc = State()
    obmen = State()
    price = State()
    izoh = State()
    receipt = State()

class BuyAd(StatesGroup):
    budget = State()
    gc = State()
    malumot = State()
    receipt = State()

class MyAds(StatesGroup):
    new_price = State()

# --- KLAVIATURALAR ---
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Elon berish")],
            [KeyboardButton(text="Elon narxlari"), KeyboardButton(text="Elonlarim")],
            [KeyboardButton(text="Adminlar")]
        ],
        resize_keyboard=True
    )

def ad_types_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Sotish eloni"), KeyboardButton(text="Olish eloni")],
            [KeyboardButton(text="⬅️ Ortga")]
        ],
        resize_keyboard=True
    )

def yes_no_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅"), KeyboardButton(text="❎")]
        ],
        resize_keyboard=True
    )

def only_exchange_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Faqat obmen")]
        ],
        resize_keyboard=True
    )

def payment_inline_btn():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="To'lov qildim ✅", callback_data="paid_receipt")]
        ]
    )

def admin_approve_menu(ad_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{ad_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{ad_id}")
            ]
        ]
    )

def my_ads_menu(ad_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Narxni tushirish", callback_data=f"discount_{ad_id}")],
            [InlineKeyboardButton(text="🤝 Sotildi", callback_data=f"sold_{ad_id}")]
        ]
    )

def sub_inline_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL.replace('@', '')}")],
            [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")]
        ]
    )

# --- QOIDALAR VA SPAM FILTER ---
def has_links(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r'(@|t\.me|http|www)', text, re.IGNORECASE))

# --- OBUNANI TEKSHIRISH FUNKSIYASI ---
async def is_subscribed(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL, user_id=user_id)
        return member.status not in ["left", "kicked"]
    except Exception:
        return False 

# --- ASOSIY HANDLERLAR ---
@dp.message(CommandStart())
@dp.message(Command("restart"))
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    if await is_subscribed(message.from_user.id):
        await message.answer("Assalomu alaykum! E'lon berish botiga xush kelibsiz.", reply_markup=main_menu())
    else:
        text = "Hurmatli foydalanuvchi!\n\nBotdan to'liq foydalanish va e'lon berish uchun avval bizning rasmiy kanalimizga obuna bo'lishingiz kerak."
        await message.answer(text, reply_markup=sub_inline_menu())

@dp.callback_query(F.data == "check_sub")
async def check_sub_handler(call: types.CallbackQuery):
    if await is_subscribed(call.from_user.id):
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.message.answer("✅ Obuna tasdiqlandi! Bosh menyudasiz.", reply_markup=main_menu())
    else:
        await call.answer("❌ Hali kanalga obuna bo'lmadingiz!", show_alert=True)

@dp.message(F.text == "⬅️ Ortga")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Bosh sahifaga qaytdingiz.", reply_markup=main_menu())

@dp.message(F.text == "Adminlar")
async def show_admins(message: types.Message):
    text = (
        "<blockquote>♻️OLDI SOTDI GARANT ADMINLAR\n"
        "Adminsiz savdo 99% aldov bilan tugaydi garand adminsiz savdo qilmang ‼️\n\n"
        "Garand admin🧑‍💻:\n"
        "👤@uzefowner\n"
        "👤@SA1DOV707\n"
        "👤@eF_LM10\n"
        "👤@Makhmudov_og</blockquote>"
    )
    await message.answer(text)

@dp.message(F.text == "Elon narxlari")
async def elon_narxlari(message: types.Message):
    text = (
        "🛍Akkauntlarga e'lon berish narxlari:\n"
        "Har qanaqa akkaunt narxi 2000 ming so'm\n\n"
        "❗️Akkount olaman deb reklama berishingiz ham mumkin!"
    )
    await message.answer(text)

@dp.message(F.text == "Elon berish")
async def elon_berish(message: types.Message, state: FSMContext):
    await state.clear()
    if await is_subscribed(message.from_user.id):
        await message.answer("Qanday turdagi elon joylamoqchisiz?\n\nE'lon joylashni boshlash uchun pastdagi tugmalardan foydalanishingiz kerak", reply_markup=ad_types_menu())
    else:
        text = "E'lon berish uchun avval kanalimizga obuna bo'ling!"
        await message.answer(text, reply_markup=sub_inline_menu())

# ================= SOTISH ELONI LOGIKASI =================
@dp.message(F.text == "Sotish eloni")
async def start_sell_ad(message: types.Message, state: FSMContext):
    if not await is_subscribed(message.from_user.id):
        await message.answer("E'lon berish uchun kanalga obuna bo'ling!", reply_markup=sub_inline_menu())
        return
    await message.answer("Shu ko'rinishda asosiy tarkib rasmini yuboring :", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(SellAd.image)

@dp.message(SellAd.image, F.photo)
async def sell_image(message: types.Message, state: FSMContext):
    # 2 ta rasm kelsa bloklash
    if message.media_group_id:
        await message.answer("❌ Iltimos, bir nechta rasm emas, faqat bitta asosiy rasmni yuboring!")
        return
        
    await state.update_data(photo_id=message.photo[-1].file_id)
    await message.answer("Qabul qilindi, akkountingizga Google yoki Game Center ulanganmi? ✅ ❎", reply_markup=yes_no_menu())
    await state.set_state(SellAd.gc)

@dp.message(SellAd.image)
async def sell_image_invalid(message: types.Message):
    await message.answer("Iltimos, rasm yuboring!")

@dp.message(SellAd.gc, F.text.in_(["✅", "❎"]))
async def sell_gc(message: types.Message, state: FSMContext):
    gc_status = "Ulangan" if message.text == "✅" else "Toza"
    await state.update_data(gc=gc_status)
    await message.answer("Qabul qilindi, ushbu akkountingizga obmen korasizmi? ✅ ❎", reply_markup=yes_no_menu())
    await state.set_state(SellAd.obmen)

@dp.message(SellAd.obmen, F.text.in_(["✅", "❎"]))
async def sell_obmen(message: types.Message, state: FSMContext):
    obmen_status = "Bor" if message.text == "✅" else "Yo'q"
    await state.update_data(obmen=obmen_status)
    await message.answer("Akkountingiz sotiladimi yoki obmen uchunmi?\n\nNarxni kiritish(Qabul qilindi, ushbu akkount narxini yuboring:\nMasalan: 100000)", reply_markup=only_exchange_menu())
    await state.set_state(SellAd.price)

@dp.message(SellAd.price)
async def sell_price(message: types.Message, state: FSMContext):
    text = message.text
    if has_links(text):
        await message.answer("Ogohlantirish! Reklama taqiqlangan (@, t.me, havolalar). Iltimos, faqat narxni kiriting:")
        return
        
    # Faqat raqam ekanligini tekshirish
    is_number = text.replace(' ', '').replace('.', '').replace(',', '').isdigit()
    if text != "Faqat obmen" and not is_number:
        await message.answer("❌ Iltimos, narxni faqat raqamlarda kiriting (masalan: 150000) yoki pastdagi 'Faqat obmen' tugmasini bosing:")
        return

    price_safe = html.escape(text)
    await state.update_data(price=price_safe)
    await message.answer("Akkountga qo'shimcha izoh yozishingiz mumkin", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(SellAd.izoh)

@dp.message(SellAd.izoh)
async def sell_izoh(message: types.Message, state: FSMContext):
    if has_links(message.text):
        await message.answer("Ogohlantirish! Reklama taqiqlangan (@, t.me, havolalar). Iltimos, izohni to'g'ri kiriting:")
        return
    
    data = await state.get_data()
    izoh = html.escape(message.text)
    price = data['price']
    
    tags = "#SOTILMAYDI #FAQAT_OBMEN" if price.lower() == "faqat obmen" else "#SOTILADI"
    narx_text = "#OBMEN_UCHUN" if price.lower() == "faqat obmen" else f"{price}"
    
    user_mention = f"<a href='tg://user?id={message.from_user.id}'>{html.escape(message.from_user.first_name)}</a>"

    ad_text = (
        f"{tags}\n\n"
        f"💴 Narx: {narx_text}\n"
        f"♻️ Obmen ko'rish: {data['obmen']}\n"
        f"⚠️ Google & Game Center: {data['gc']}\n"
        f"☎️ Murojaat: {user_mention}\n\n"
        f"📋 Qo'shilgan ma'lumot:\n"
        f"<blockquote>{izoh}</blockquote>\n\n"
        f"<blockquote>♻️OLDI SOTDI GARANT ADMINLAR\n"
        f"Adminsiz savdo 99% aldov bilan tugaydi garand adminsiz savdo qilmang ‼️\n\n"
        f"Garand admin🧑‍💻:\n"
        f"👤@uzefowner\n"
        f"👤@SA1DOV707\n"
        f"👤@eF_LM10\n"
        f"👤@Makhmudov_og</blockquote>\n\n"
        f"Reklama berish uchun 📣:\n"
        f"{BOT_USERNAME} ⚜️"
    )

    await state.update_data(final_text=ad_text)
    
    if message.from_user.id == ADMIN_ID:
        await publish_ad(message.from_user.id, "sell", data['photo_id'], ad_text, price)
        await message.answer("Admin ekani tasdiqlandi. E'lon kanalga joylandi!", reply_markup=main_menu())
        await state.clear()
        return

    payment_msg = (
        "✅ E'lon yuborishga tayyor!\n\n"
        f"📢 Kanalimiz: {CHANNEL}\n"
        "💰 Xizmat narxi: 2 000 so'm\n"
        "Admin karta raqami ;\n"
        "9860166654505204\n"
        "Sunnatov Shukurullo\n\n"
        "⏳ 5 daqiqa ichida to'lov qiling.\n"
        "💳 To'lov o'tishi bilan e'lon avtomat joylanadi.\n\n"
        "(Avto-joylanmasa, vaqt tugagach chek yuborishingiz mumkin)."
    )
    await message.answer_photo(photo=data['photo_id'], caption=ad_text)
    await message.answer(payment_msg, reply_markup=payment_inline_btn())
    await state.set_state(SellAd.receipt)

# ================= OLISH ELONI LOGIKASI =================
@dp.message(F.text == "Olish eloni")
async def start_buy_ad(message: types.Message, state: FSMContext):
    if not await is_subscribed(message.from_user.id):
        await message.answer("E'lon berish uchun kanalga obuna bo'ling!", reply_markup=sub_inline_menu())
        return
    await message.answer("💵 Elon uchun budjetingizni yuboring:\n\nMasalan: 500000", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(BuyAd.budget)

@dp.message(BuyAd.budget)
async def buy_budget(message: types.Message, state: FSMContext):
    text = message.text
    if has_links(text):
        await message.answer("Ogohlantirish! Reklama taqiqlangan (@, t.me, havolalar).")
        return
        
    # Faqat raqam ekanligini tekshirish
    is_number = text.replace(' ', '').replace('.', '').replace(',', '').isdigit()
    if not is_number:
        await message.answer("❌ Iltimos, budjetni faqat raqamlarda kiriting (masalan: 150000):")
        return

    budget_safe = html.escape(text)
    await state.update_data(budget=budget_safe)
    await message.answer("🔐 Qabul qilindi, Google yoki Game Center akkount ko'rasizmi? ✅ ❎", reply_markup=yes_no_menu())
    await state.set_state(BuyAd.gc)

@dp.message(BuyAd.gc, F.text.in_(["✅", "❎"]))
async def buy_gc(message: types.Message, state: FSMContext):
    tag = "#OLINADI #FAQAT_TOZA" if message.text == "❎" else "#OLINADI"
    await state.update_data(tag=tag)
    await message.answer("📝 Qanday akkaunt kerakligini to'liq yozing:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(BuyAd.malumot)

@dp.message(BuyAd.malumot)
async def buy_malumot(message: types.Message, state: FSMContext):
    if has_links(message.text):
        await message.answer("Ogohlantirish! Reklama taqiqlangan (@, t.me, havolalar).")
        return

    data = await state.get_data()
    malumot = html.escape(message.text)
    budget = data['budget']
    user_mention = f"<a href='tg://user?id={message.from_user.id}'>{html.escape(message.from_user.first_name)}</a>"

    ad_text = (
        f"{data['tag']}\n\n"
        f"💴 BUDJET: {budget}\n"
        f"📋 Ma'lumot:\n"
        f"<blockquote>{malumot}</blockquote>\n"
        f"☎️ Murojaat: {user_mention}\n\n"
        f"<blockquote>♻️OLDI SOTDI GARANT ADMINLAR\n"
        f"Adminsiz savdo 99% aldov bilan tugaydi garand adminsiz savdo qilmang ‼️\n\n"
        f"Garand admin🧑‍💻:\n"
        f"👤@uzefowner\n"
        f"👤@SA1DOV707\n"
        f"👤@eF_LM10\n"
        f"👤@Makhmudov_og</blockquote>\n\n"
        f"Reklama berish uchun 📣:\n"
        f"{BOT_USERNAME} ⚜️"
    )
    
    await state.update_data(final_text=ad_text, price=budget)

    if message.from_user.id == ADMIN_ID:
        await publish_ad(message.from_user.id, "buy", None, ad_text, budget)
        await message.answer("Admin ekani tasdiqlandi. E'lon kanalga joylandi!", reply_markup=main_menu())
        await state.clear()
        return

    payment_msg = (
        "✅ E'lon yuborishga tayyor!\n\n"
        f"📢 Kanalimiz: {CHANNEL}\n"
        "💰 Xizmat narxi: 2 000 so'm\n"
        "Admin karta raqami ;\n"
        "9860166654505204\n"
        "Sunnatov Shukurullo\n\n"
        "⏳ 5 daqiqa ichida to'lov qiling.\n"
        "💳 To'lov o'tishi bilan e'lon avtomat joylanadi.\n\n"
        "(Avto-joylanmasa, vaqt tugagach chek yuborishingiz mumkin)."
    )
    await message.answer(ad_text)
    await message.answer(payment_msg, reply_markup=payment_inline_btn())
    await state.set_state(BuyAd.receipt)

# ================= TO'LOV VA ADMIN TASDIQLASHI =================
@dp.callback_query(F.data == "paid_receipt", StateFilter(SellAd.receipt, BuyAd.receipt))
async def ask_receipt(call: types.CallbackQuery):
    await call.message.answer("To'lov chekini rasm ko'rinishida yuboring:")
    await call.answer()

@dp.message(StateFilter(SellAd.receipt, BuyAd.receipt), F.photo)
async def receive_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ad_type = "sell" if "photo_id" in data else "buy"
    photo_id = data.get("photo_id", "")
    
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO ads (user_id, type, photo_id, text_content, price, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    ''', (message.from_user.id, ad_type, photo_id, data['final_text'], data['price']))
    ad_id = cur.lastrowid
    conn.commit()
    conn.close()

    admin_text = f"Yangi to'lov cheki!\nUser ID: {message.from_user.id}\nUsername: @{message.from_user.username}\nE'lon turi: {ad_type}"
    await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=admin_approve_menu(ad_id))
    
    await message.answer("Chek adminga yuborildi. Tasdiqlangach e'lon kanalga joylanadi.", reply_markup=main_menu())
    await state.clear()

@dp.callback_query(F.data.startswith("approve_"))
async def admin_approve(call: types.CallbackQuery):
    ad_id = int(call.data.split("_")[1])
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("SELECT user_id, type, photo_id, text_content, price FROM ads WHERE id = ?", (ad_id,))
    ad_data = cur.fetchone()
    
    if ad_data:
        user_id, ad_type, photo_id, text_content, price = ad_data
        msg_id = await publish_ad(user_id, ad_type, photo_id, text_content, price)
        
        cur.execute("UPDATE ads SET status = 'active', message_id = ? WHERE id = ?", (msg_id, ad_id))
        
        try:
            await bot.send_message(user_id, "✅ To'lovingiz tasdiqlandi va e'lon kanalga joylandi!")
        except Exception:
            pass 
            
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
        try:
            await bot.send_message(ad_data[0], "❌ To'lovingiz tasdiqlanmadi. Iltimos, adminga murojaat qiling.")
        except Exception:
            pass
        cur.execute("UPDATE ads SET status = 'rejected' WHERE id = ?", (ad_id,))
    
    conn.commit()
    conn.close()
    
    await call.message.edit_caption(caption=call.message.caption + "\n\n❌ RAD ETILDI")
    await call.answer()

async def publish_ad(user_id, ad_type, photo_id, text_content, price) -> int:
    if ad_type == "sell" and photo_id:
        msg = await bot.send_photo(chat_id=CHANNEL, photo=photo_id, caption=text_content)
    else:
        msg = await bot.send_message(chat_id=CHANNEL, text=text_content)
    
    if user_id == ADMIN_ID:
        conn = sqlite3.connect("bot_database.db")
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO ads (user_id, type, photo_id, text_content, message_id, price, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
        ''', (user_id, ad_type, photo_id if photo_id else "", text_content, msg.message_id, price))
        conn.commit()
        conn.close()

    return msg.message_id

# ================= ELONLARIM VA NARX TUSHIRISH =================
@dp.message(F.text == "Elonlarim")
async def my_ads(message: types.Message):
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("SELECT id, message_id, price, discount_count FROM ads WHERE user_id = ? AND status = 'active'", (message.from_user.id,))
    active_ads = cur.fetchall()
    conn.close()

    if not active_ads:
        await message.answer("Sizda faol e'lonlar mavjud emas.")
        return 
    
    for ad in active_ads:
        ad_id, msg_id, price, discount_count = ad
        link = f"https://t.me/{CHANNEL.replace('@', '')}/{msg_id}"
        text = f"Reklama: {link}\nJoriy narx: {price}"
        
        await message.answer(text, reply_markup=my_ads_menu(ad_id), disable_web_page_preview=True)

@dp.callback_query(F.data.startswith("discount_"))
async def ask_discount(call: types.CallbackQuery, state: FSMContext):
    ad_id = int(call.data.split("_")[1])
    
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("SELECT discount_count FROM ads WHERE id = ?", (ad_id,))
    res = cur.fetchone()
    conn.close()

    if res and res[0] >= 2:
        await call.answer("Siz bu e'lon narxini maksimal 2 marta tushirgansiz!", show_alert=True)
        return
    
    await state.update_data(ad_id=ad_id)
    await call.message.answer("Yangi narxni kiriting:")
    await state.set_state(MyAds.new_price)
    await call.answer()

@dp.message(MyAds.new_price)
async def process_discount(message: types.Message, state: FSMContext):
    text = message.text
    if has_links(text):
        await message.answer("Ogohlantirish! Reklama taqiqlangan (@, t.me, havolalar).")
        return
        
    is_number = text.replace(' ', '').replace('.', '').replace(',', '').isdigit()
    if not is_number:
        await message.answer("❌ Iltimos, yangi narxni faqat raqamlarda kiriting:")
        return

    new_price = html.escape(text)
    data = await state.get_data()
    ad_id = data['ad_id']

    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("SELECT message_id, price, discount_count FROM ads WHERE id = ?", (ad_id,))
    ad_data = cur.fetchone()

    if ad_data:
        msg_id, old_price, discount_count = ad_data
        try:
            fast_text = f"#FAST Yangi narxi: <s>{old_price}</s>  {new_price}"
            await bot.send_message(chat_id=CHANNEL, text=fast_text, reply_to_message_id=msg_id)
            
            cur.execute("UPDATE ads SET price = ?, discount_count = discount_count + 1 WHERE id = ?", (new_price, ad_id))
            conn.commit()
            await message.answer("Narx muvaffaqiyatli tushirildi va kanalga belgilandi!", reply_markup=main_menu())
        except Exception as e:
            await message.answer(f"Xatolik yuz berdi: {e}")
    
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
        msg_id = ad_data[0]
        try:
            await bot.send_message(chat_id=CHANNEL, text="#SOTILDI", reply_to_message_id=msg_id)
            cur.execute("UPDATE ads SET status = 'sold' WHERE id = ?", (ad_id,))
            conn.commit()
            await call.message.edit_text(call.message.text + "\n\n✅ SOTILDI deb belgilandi.")
            await call.answer("E'lon sotildi deb belgilandi!", show_alert=True)
        except Exception as e:
            await call.answer(f"Xatolik: {e}", show_alert=True)

    conn.close()

# --- ISHGA TUSHIRISH ---
async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
