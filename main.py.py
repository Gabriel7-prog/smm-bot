import asyncio
import logging
import sqlite3
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8829325745:AAHURBdvGt_55e6HnKR-ncFULTD5HNIsFZ8"
SMM24_API_KEY = "0677be5ea5d88b8294fde967d35584ac"
SMM24_API_URL = "https://smm24.uz/api/v2"

CARD_NUMBER = "5614 6821 1432 5626"
CARD_HOLDER = "Tillavoldiyev Javohir"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# ==================== DATABASE (DATABASE.DB) ====================
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_user_balance(user_id: int) -> int:
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row is None:
        cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 0))
        conn.commit()
        balance = 0
    else:
        balance = row[0]
    conn.close()
    return balance

def add_user_balance(user_id: int, amount: int):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# ==================== FSM STATES ====================
class DepositState(StatesGroup):
    waiting_for_amount = State()

class SMMOrderState(StatesGroup):
    waiting_for_link = State()

# ==================== SMM24.UZ API HELPER ====================
async def smm24_create_order(service_id: int, link: str, quantity: int):
    params = {
        'key': SMM24_API_KEY,
        'action': 'add',
        'service': service_id,
        'link': link,
        'quantity': quantity
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(SMM24_API_URL, data=params) as resp:
            return await resp.json()

# ==================== CHIROYLI MENYULAR (KEYBOARDS) ====================
def main_menu_kb(user_id: int):
    balance = get_user_balance(user_id)
    kb = [
        [InlineKeyboardButton(text="🚀 SMM Nakrutka", callback_data="smm"), InlineKeyboardButton(text="📱 Virtual Nomer", callback_data="number")],
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="stars"), InlineKeyboardButton(text="🎁 Gifts & NFT", callback_data="gifts")],
        [InlineKeyboardButton(text=f"💳 Balans: {balance:,} so'm", callback_data="deposit"), InlineKeyboardButton(text="👤 Profil", callback_data="profile")],
        [InlineKeyboardButton(text="👨‍💻 Qo'llab-quvvatlash", url="https://t.me/admin")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def smm_menu_kb():
    kb = [
        [InlineKeyboardButton(text="✈️ Telegram Obunachi", callback_data="smm_tg_sub")],
        [InlineKeyboardButton(text="👁️ Telegram Ko'rishlar", callback_data="smm_tg_view")],
        [InlineKeyboardButton(text="📸 Instagram Layk/Follow", callback_data="smm_insta")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def back_to_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")]])

# ==================== HANDLERS (LOGIKA) ====================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    init_db()
    get_user_balance(message.from_user.id)
    text = (
        f"👋 Xush kelibsiz, {message.from_user.first_name}!\n\n"
        f"Bot orqali SMM xizmatlari, Telegram Stars, Gifts va Virtual raqamlarni avtomatik xarid qilishingiz mumkin."
    )
    await message.answer(text, reply_markup=main_menu_kb(message.from_user.id), parse_mode="Markdown")

@dp.callback_query(F.data == "back_main")
async def back_main_handler(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "Bosh menyudasiz. Kerakli bo'limni tanlang:",
        reply_markup=main_menu_kb(call.from_user.id)
    )
    await call.answer()

# --- HISOB TO'LDIRISH (FSM) ---
@dp.callback_query(F.data == "deposit")
async def deposit_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(DepositState.waiting_for_amount)
    await call.message.edit_text(
        "💳 Hisobni to'ldirish\n\n"
        "Qancha summa to'lamoqchisiz?\n"
        "📌 *Minimal summa:* 1,000 so'm\n"
        "📌 *Maksimal summa:* 100,000 so'm\n\n"
        "Summani faqat raqamlarda kiriting (Masalan: 15000):",
        reply_markup=back_to_main_kb(),
        parse_mode="Markdown"
    )
    await call.answer()

@dp.message(DepositState.waiting_for_amount)
async def process_deposit_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Iltimos, faqat raqamlardan iborat summa kiriting (masalan: 10000):")
        return

    amount = int(message.text)
    if amount < 1000 or amount > 100000:
        await message.answer("⚠️ Summa 1 000 so'm va 100 000 so'm oralig'ida bo'lishi kerak!")
        return

    await state.clear()
    
    pay_text = (
        f"✅ To'lov buyurtmasi yaratildi!\n\n"
        f"💰 To'lov summasi: {amount:,} so'm\n\n"
        f"💳 Karta raqami: {CARD_NUMBER}\n"
        f"👤 Eshatuvchi: {CARD_HOLDER}\n\n"
        f"👇 Quyidagi tugma orqali to'lov ilovasiga o'tib, ko'rsatilgan summani o'tkazing va chekni adminga yuboring."
    )
    
    pay_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔹 Click orqali to'lash", url="https://my.click.uz/")],
        [InlineKeyboardButton(text="🔹 Payme orqali to'lash", url="https://payme.uz/")],
        [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_main")]
    ])
    
    await message.answer(pay_text, reply_markup=pay_kb, parse_mode="Markdown")

# --- SMM BO'LIMI ---
@dp.callback_query(F.data == "smm")
async def smm_section(call: CallbackQuery):
    await call.message.edit_text(
        "🚀 SMM Nakrutka Xizmatlari\n\nKerakli tarmoq va xizmat turini tanlang:",
        reply_markup=smm_menu_kb(),
        parse_mode="Markdown"
    )
    await call.answer()

# --- PROFIL BO'LIMI ---
@dp.callback_query(F.data == "profile")
async def profile_section(call: CallbackQuery):
    bal = get_user_balance(call.from_user.id)
    text = (
        f"👤 Sizning Profilingiz\n\n"
        f"🆔 ID: {call.from_user.id}\n"
        f"👤 Ism: {call.from_user.first_name}\n"
        f"💰 Balans: {bal:,} so'm"
    )
    await call.message.edit_text(text, reply_markup=back_to_main_kb(), parse_mode="Markdown")
    await call.answer()

# --- STARS & GIFTS BO'LIMLARI ---
@dp.callback_query(F.data == "stars")
async def stars_section(call: CallbackQuery):
    await call.message.edit_text(
        "⭐ Telegram Stars Xarid Qiling\n\nTez kunda avtomatik tushirish tizimi ulanadi!",
        reply_markup=back_to_main_kb(),
        parse_mode="Markdown"
    )
    await call.answer()

@dp.callback_query(F.data == "gifts")
async def gifts_section(call: CallbackQuery):
    await call.message.edit_text(
        "🎁 Gifts & NFT Yuborish\n\n"
        "- Anonim yoki Ochiq yuborish\n"
        "- Xabar bilan yoki xabarsiz\n\n*(Tez kunda ishga tushadi)*",
        reply_markup=back_to_main_kb(),
        parse_mode="Markdown"
    )
    await call.answer()
@dp.callback_query(F.data == "number")
async def number_section(call: CallbackQuery):
    await call.message.edit_text(
        "📱 Virtual Raqamlar Bo'limi\n\nSMS kodlarni qabul qilish paneli tayyorlanmoqda...",
        reply_markup=back_to_main_kb(),
        parse_mode="Markdown"
    )
    await call.answer()

# ==================== MAIN RUN ====================
async def main():
    init_db()
    print("Bot yangi kalitlar bilan ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
