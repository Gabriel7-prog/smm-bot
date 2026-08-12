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

ADMIN_ID = 7975481978

CARD_NUMBER = "5614 6821 1432 5626"
CARD_HOLDER = "Tillavoldiyev Javohir"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# ==================== DATABASE ====================
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
    waiting_for_receipt = State()

# ==================== CHIROYLI MENYULAR ====================
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

# ==================== HANDLERS ====================

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
async def back_main_handler(call:CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "Bosh menyudasiz. Kerakli bo'limni tanlang:",
        reply_markup=main_menu_kb(call.from_user.id)
    )
    await call.answer()

# --- HISOB TO'LDIRISH TIZIMI ---
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
    if not message.text or not message.text.isdigit():
        await message.answer("❌ Iltimos, faqat raqamlardan iborat summa kiriting (masalan: 10000):")
        return

    amount = int(message.text)
    if amount < 1000 or amount > 100000:
        await message.answer("⚠️ Summa 1 000 so'm va 100 000 so'm oralig'ida bo'lishi kerak!")
        return

    await state.update_data(deposit_amount=amount)
    await state.set_state(DepositState.waiting_for_receipt)
    
    pay_text = (
        f"✅ To'lov buyurtmasi yaratildi!\n\n"
        f"💰 To'lov summasi: {amount:,} so'm\n\n"
        f"💳 Karta raqami: {CARD_NUMBER}\n"
        f"👤 Egasining ismi: {CARD_HOLDER}\n\n"
        f"📸 Endi to'lov chekining rasmini (skrinshotini) shu yerga yuboring!"
    )
    
    pay_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔹 Click", url="https://my.click.uz/"), InlineKeyboardButton(text="🔹 Payme", url="https://payme.uz/")],
        [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="back_main")]
    ])
    
    await message.answer(pay_text, reply_markup=pay_kb, parse_mode="Markdown")

# --- CHEK QABUL QILISH VA ADMINGA YUBORISH ---
@dp.message(DepositState.waiting_for_receipt, F.photo)
async def process_receipt_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("deposit_amount")
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
    photo_id = message.photo[-1].file_id

    await state.clear()
    await message.answer("⏳ To'lov chekingiz adminga yuborildi!\nTasdiqlangach, balansingizga pul tushadi.", reply_markup=main_menu_kb(user_id))

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay_approve_{user_id}_{amount}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"pay_reject_{user_id}")
        ]
    ])

    admin_text = (
        f"💰 YANGI TO'LOV SO'ROVI!\n\n"
        f"👤 Foydalanuvchi: {message.from_user.first_name} ({username})\n"
        f"🆔 ID: {user_id}\n"
        f"💵 Summa: {amount:,} so'm"
    )

    try:
        await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_text, reply_markup=admin_kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Adminga xabar yuborishda xatolik: {e}")

# --- ADMIN TASDIQLASH / BEKOR QILISH ---
@dp.callback_query(F.data.startswith("pay_approve_"))
async def approve_payment(call: CallbackQuery):
    _, _, user_id_str, amount_str = call.data.split("_")
    target_user_id = int(user_id_str)
    amount = int(amount_str)

    add_user_balance(target_user_id, amount)
    new_bal = get_user_balance(target_user_id)

    await call.message.edit_caption(
        caption=call.message.caption + f"\n\n✅ TASDIQLANDI! (Balansga {amount:,} so'm qo'shildi)",
        reply_markup=None
    )
    await call.answer("To'lov tasdiqlandi!")
    try:
        await bot.send_message(
            chat_id=target_user_id,
            text=f"🎉 Hisobingiz to'ldirildi!\n\n💰 Qo'shildi: {amount:,} so'm\n💳 Joriy balans: {new_bal:,} so'm",
            parse_mode="Markdown"
        )
    except Exception:
        pass

@dp.callback_query(F.data.startswith("pay_reject_"))
async def reject_payment(call: CallbackQuery):
    target_user_id = int(call.data.split("_")[2])

    await call.message.edit_caption(
        caption=call.message.caption + "\n\n❌ RAD ETILDI!",
        reply_markup=None
    )
    await call.answer("To'lov rad etildi.")

    try:
        await bot.send_message(
            chat_id=target_user_id,
            text="❌ Sizning to'lov so'rovingiz rad etildi.\nIltimos, chek to'g'riligini tekshirib adminga murojaat qiling."
        )
    except Exception:
        pass

# --- BOSHQA BO'LIMLAR ---
@dp.callback_query(F.data == "smm")
async def smm_section(call: CallbackQuery):
    await call.message.edit_text("🚀 SMM Nakrutka Xizmatlari\n\nKerakli tarmoqni tanlang:", reply_markup=smm_menu_kb(), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "profile")
async def profile_section(call: CallbackQuery):
    bal = get_user_balance(call.from_user.id)
    text = f"👤 Sizning Profilingiz\n\n🆔 ID: {call.from_user.id}\n👤 Ism: {call.from_user.first_name}\n💰 Balans: {bal:,} so'm"
    await call.message.edit_text(text, reply_markup=back_to_main_kb(), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "stars")
async def stars_section(call: CallbackQuery):
    await call.message.edit_text("⭐ Telegram Stars\n\nTez kunda ishga tushadi!", reply_markup=back_to_main_kb(), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "gifts")
async def gifts_section(call: CallbackQuery):
    await call.message.edit_text("🎁 Gifts & NFT\n\nTez kunda ishga tushadi!", reply_markup=back_to_main_kb(), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "number")
async def number_section(call: CallbackQuery):
    await call.message.edit_text("📱 Virtual Raqamlar\n\nTez kunda ishga tushadi!", reply_markup=back_to_main_kb(), parse_mode="Markdown")
    await call.answer()

# ==================== MAIN RUN ====================
async def main():
    init_db()
    print("Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
