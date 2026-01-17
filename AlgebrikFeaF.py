import asyncio
import logging
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import google.generativeai as genai

# --- KONFIGURATSIYA ---
TOKEN = "8554256376:AAFDgX0dj7hbaxNvGioRe61x56wHUJOsTn0"
ADMIN_ID = 7829422043
CHANNELS = [
    {"id": -1003646737157, "link": "https://t.me/Disney_Multfilmlar1", "name": "1-Kanal"},
    {"id": -1003155796926, "link": "https://t.me/FeaF_Helping", "name": "2-Kanal"},
    {"id": 7696636612, "link": "https://t.me/Pul_toplaymizuz_bot", "name": "3-Bot (Obuna)"}
]

# Gemini AI sozlamasi (API_KEY ni o'zgartiring)
genai.configure(api_key="AIzaSyCZUQwzuyo3KlKl8SovTK_e2EPh-6akS68") 
model = genai.GenerativeModel('gemini-1.5-flash')

# Ma'lumotlar bazasi o'rniga vaqtinchalik lug'at
users_db = {} # {user_id: {'name': name, 'count': 0}}
active_state = {} # Foydalanuvchi qaysi bo'limdaligini bilish uchun

# --- FLASK (UPTIMEROBOT UCHUN) ---
app = Flask('')
@app.route('/')
def home(): return "Bot ishlayapti!"

def run(): app.run(host='0.0.0.0', port=8080)

# --- BOT QISMI ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Majburiy obuna tekshiruvi
async def check_sub(user_id):
    not_subbed = []
    for channel in CHANNELS:
        try:
            status = await bot.get_chat_member(chat_id=channel['id'], user_id=user_id)
            if status.status in ['left', 'kicked']:
                not_subbed.append(channel)
        except:
            not_subbed.append(channel)
    return not_subbed

# Asosiy menyu
def main_menu(is_admin=False):
    kb = [
        [KeyboardButton(text="🧮 Matematika masala"), KeyboardButton(text="🎬 Video yuklab olish")],
        [KeyboardButton(text="✍️ Murojat")]
    ]
    if is_admin:
        kb.append([KeyboardButton(text="📢 Post joylash"), KeyboardButton(text="📊 Statistika")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- HANDLERLAR ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.full_name
    if user_id not in users_db:
        users_db[user_id] = {'name': name, 'count': 0}
    
    await message.answer(
        f"👋 Salom {name}! Men matematika vazifalarida senga yordam bera olaman, xuddi Gemini kabi. 🤖\n\n"
        f"Iltimos, misolni o'zini yuboring yoki rasmga olib yuboring. Men faqat matematik masalalarni tushunaman! ✨",
        reply_markup=main_menu(user_id == ADMIN_ID)
    )

@dp.message(F.text == "🧮 Matematika masala")
async def math_start(message: types.Message):
    await message.answer("📝 Misolni matn ko'rinishida yoki rasm holatida yuboring...")
    active_state[message.from_user.id] = 'math'

@dp.message(F.text == "🎬 Video yuklab olish")
async def video_start(message: types.Message):
    await message.answer(f"📥 {message.from_user.first_name}, yuklab olish kerak bo'lgan video linkini yuboring:")
    active_state[message.from_user.id] = 'video'

@dp.message(F.text == "✍️ Murojat")
async def contact_admin(message: types.Message):
    await message.answer(f"📞 {message.from_user.first_name}, adminga murojatingizni yozing:")
    active_state[message.from_user.id] = 'contact'

@dp.message(F.text == "📊 Statistika")
async def show_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    total = len(users_db)
    # Eng faol 3 ta (misol yechganlar soni bo'yicha)
    top_users = sorted(users_db.items(), key=lambda x: x[1]['count'], reverse=True)[:3]
    text = f"📊 **Statistika:**\n👥 Jami foydalanuvchilar: {total}\n\n🏆 **Top 3 foydalanuvchi:**\n"
    for i, (uid, data) in enumerate(top_users, 1):
        text += f"{i}. {data['name']} - {data['count']} ta misol\n"
    await message.answer(text)

# Oddiy matnli xabarlar va Gemini integratsiyasi
@dp.message()
async def handle_all(message: types.Message):
    user_id = message.from_user.id
    state = active_state.get(user_id)

    # Obunani tekshirish
    not_subbed = await check_sub(user_id)
    if not_subbed:
        builder = InlineKeyboardBuilder()
        for ch in not_subbed:
            builder.row(InlineKeyboardButton(text=ch['name'], url=ch['link']))
        builder.row(InlineKeyboardButton(text="✅ Tekshirish", callback_data="check"))
        return await message.answer(f"❌ {message.from_user.first_name}, botdan foydalanish uchun kanallarga obuna bo'ling:", reply_markup=builder.as_markup())

    # Raxmat javobi
    if message.text and "raxmat" in message.text.lower():
        return await message.answer("😇 Arzimaydi! Doimo senga yordam berishga tayyorman! 🚀")

    # Matematika yechish (Text yoki Rasm)
    if state == 'math' or message.photo or message.text:
        msg_wait = await message.answer("🔄 Masala tahlil qilinmoqda, iltimos kuting...")
        try:
            # Gemini-ga yuborish
            prompt = f"Ushbu matematik masalani batafsil tushuntirib yechib ber: {message.text if message.text else ''}"
            response = model.generate_content(prompt)
            users_db[user_id]['count'] += 1
            await msg_wait.edit_text(
                f"✅ {message.from_user.first_name}, mana yuborgan masalang javobi:\n\n{response.text}\n\n"
                f"📍 Masala @Boldaham_bot yordamida bajarildi."
            )
        except Exception as e:
            await msg_wait.edit_text("😔 Kechirasiz, masalani yechishda xatolik yuz berdi.")

# Botni ishga tushirish
async def main():
    Thread(target=run).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
