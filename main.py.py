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

# ==================== MENYULAR ====================
def main_menu_kb(user_id: int):
    balance = get_user_balance(user_id)
    kb = [
        [InlineKeyboardButton(text="🚀 SMM Nakrutka", callback_data="smm"), InlineKeyboardButton(text="📱 Virtual Nomer", callback_data="number")],
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="stars"), InlineKeyboardButton(text="🎁 Gifts & NFT", callback_data="gifts")],
        [InlineKeyboardButton(text=f"💳 Balans: {balance:,} so'm", callback_data="deposit"), InlineKeyboardButton(text="👤 Profil", callback_data="profile")],
        [InlineKeyboardButton(text="👨‍💻 Qo'llab-quvvatlash", url="https://t.me/admin")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def back_to_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")]])

# ==================== HANDLERS ====================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    init_db()
    get_user_balance(message.from_user.id)
    text = f"👋 Xush kelibsiz, {message.from_user.first_name}!\n\nBot xizmatlaridan foydalanishingiz mumkin."
    await message.answer(text, reply_markup=main_menu_kb(message.from_user.id), parse_mode="Markdown")

@dp.callback_query(F.data == "back_main")
async def back_main_handler(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Bosh menyudasiz. Kerakli bo'limni tanlang:", reply_markup=main_menu_kb(call.from_user.id))
    await call.answer()

@dp.callback_query(F.data == "deposit")
async def deposit_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(DepositState.waiting_for_amount)
    await call.message.edit_text(
        "💳 Hisobni to'ldirish\n\nSummani raqamlarda kiriting (masalan: 15000):",
        reply_markup=back_to_main_kb(),
        parse_mode="Markdown"
    )
    await call.answer()
@dp.message(DepositState.waiting_for_amount)
async def process_deposit_amount(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("❌ Faqat raqamlardan iborat summa kiriting:")
        return

    amount = int(message.text)
    if amount < 1000 or amount > 100000:
        await message.answer("⚠️ Summa 1 000 so'm va 100 000 so'm oralig'ida bo'lishi kerak!")
        return

    await state.update_data(deposit_amount=amount)
    await state.set_state(DepositState.waiting_for_receipt)
    
    clean_card = CARD_NUMBER.replace(" ", "")
    click_link = f"https://my.click.uz/clicka/p2p/?card={clean_card}&amount={amount}"
    payme_link = f"https://payme.uz/{clean_card}"

    pay_text = (
        f"✅ To'lov buyurtmasi yaratildi!\n\n"
        f"💰 To'lov summasi: {amount:,} so'm\n\n"
        f"💳 Karta raqami: {CARD_NUMBER}\n"
        f"👤 Egasining ismi: {CARD_HOLDER}\n\n"
        f"👇 *Pastroqdagi tugmalarni bossangiz, ilova avtomatik ochiladi:*\n"
        f"📸 *To'lovni amalga oshirgach, chek rasmini shu yerga yuboring!*"
    )
    
    pay_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔹 Click'da ochish", url=click_link), 
            InlineKeyboardButton(text="🔹 Payme'da ochish", url=payme_link)
        ],
        [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="back_main")]
    ])
    
    await message.answer(pay_text, reply_markup=pay_kb, parse_mode="Markdown")

@dp.message(DepositState.waiting_for_receipt, F.photo)
async def process_receipt_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("deposit_amount")
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id

    await state.clear()
    await message.answer("⏳ Chekingiz adminga yuborildi!", reply_markup=main_menu_kb(user_id))

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay_approve_{user_id}_{amount}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"pay_reject_{user_id}")
        ]
    ])

    admin_text = f"💰 Yangi to'lov!\nID: {user_id}\nSumma: {amount:,} so'm"
    try:
        await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_text, reply_markup=admin_kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Xato: {e}")

@dp.callback_query(F.data.startswith("pay_approve_"))
async def approve_payment(call: CallbackQuery):
    _, _, user_id_str, amount_str = call.data.split("_")
    target_user_id = int(user_id_str)
    amount = int(amount_str)

    add_user_balance(target_user_id, amount)
    await call.message.edit_caption(caption=call.message.caption + f"\n\n✅ Tasdiqlandi (+{amount:,} so'm)")
    await call.answer("Tasdiqlandi!")
    try:
        await bot.send_message(chat_id=target_user_id, text=f"🎉 Balansingizga {amount:,} so'm qo'shildi!", parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("pay_reject_"))
async def reject_payment(call: CallbackQuery):
    target_user_id = int(call.data.split("_")[2])
    await call.message.edit_caption(caption=call.message.caption + "\n\n❌ Rad etildi")
    await call.answer("Rad etildi!")
    try:
        await bot.send_message(chat_id=target_user_id, text="❌ To'lov rad etildi.")
    except Exception:
        pass

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
