import os
import asyncio
import io
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import google.generativeai as genai

# --- SOZLAMALAR ---
TOKEN = "8554256376:AAFDgX0dj7hbaxNvGioRe61x56wHUJOsTn0"
ADMIN_ID = 7829422043
CHANNELS = [
    {"id": -1003646737157, "link": "https://t.me/Disney_Multfilmlar1", "name": "1-Kanal"},
    {"id": -1003155796926, "link": "https://t.me/FeaF_Helping", "name": "2-Kanal"},
]

# Gemini sozlamalari
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask('')

# Ma'lumotlar bazasi (vaqtincha - bot o'chib yonsa tozalanadi)
users_db = {} # {user_id: {'name': name, 'count': 0}}
active_state = {} # {user_id: state}

# --- FLASK (UPTIMEROBOT UCHUN) ---
@app.route('/')
def home(): return "Bot is running!"

def run_flask(): app.run(host='0.0.0.0', port=8080)

# --- FUNKSIYALAR ---
async def check_sub(user_id):
    not_subbed = []
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch['id'], user_id)
            if member.status in ['left', 'kicked']:
                not_subbed.append(ch)
        except Exception:
            not_subbed.append(ch)
    return not_subbed

def main_menu(is_admin=False):
    kb = ReplyKeyboardBuilder()
    kb.button(text="🧮 Matematika masala")
    kb.button(text="🎬 Video yuklab olish")
    kb.button(text="✍️ Murojat")
    if is_admin:
        kb.button(text="📢 Post joylash")
        kb.button(text="📊 Statistika")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

def back_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔙 Orqaga")
    return kb.as_markup(resize_keyboard=True)

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
    active_state[message.from_user.id] = 'math'
    await message.answer("📝 Misolni matn ko'rinishida yoki rasm holatida yuboring...", reply_markup=back_kb())

@dp.message(F.text == "🎬 Video yuklab olish")
async def video_start(message: types.Message):
    active_state[message.from_user.id] = 'video'
    await message.answer(f"{message.from_user.first_name}, yuklab olish kerak bo'lgan video linkini yuboring... 🔗", reply_markup=back_kb())

@dp.message(F.text == "✍️ Murojat")
async def contact_start(message: types.Message):
    active_state[message.from_user.id] = 'contact'
    await message.answer(f"{message.from_user.first_name}, adminga murojatingizni yozib qoldiring... 👨‍💻", reply_markup=back_kb())

@dp.message(F.text == "🔙 Orqaga")
async def go_back(message: types.Message):
    active_state[message.from_user.id] = None
    await message.answer("Asosiy menyuga qaytdingiz. 🏠", reply_markup=main_menu(message.from_user.id == ADMIN_ID))

@dp.message(F.text == "Raxmat")
async def thanks_msg(message: types.Message):
    await message.answer("😇 Arzimaydi! Doim senga yordam berishga tayyorman. Yana misollar bo'lsa yuboraver! ✨")

# --- ASOSIY ISHLOVCHI ---
@dp.message()
async def handle_all(message: types.Message):
    user_id = message.from_user.id
    state = active_state.get(user_id)

    # 1. Obunani tekshirish
    not_subbed = await check_sub(user_id)
    if not_subbed:
        builder = InlineKeyboardBuilder()
        for ch in not_subbed:
            builder.button(text=ch['name'], url=ch['link'])
        builder.button(text="✅ Tekshirish", callback_data="check")
        builder.adjust(1)
        return await message.answer(f"⚠️ {message.from_user.first_name}, botdan foydalanish uchun quyidagi kanallarga obuna bo'lishingiz kerak:", reply_markup=builder.as_markup())

    # 2. Matematika (Gemini)
    if state == 'math':
        msg = await message.answer("🤔 Masalani o'ylayapman, bir oz kuting...")
        try:
            if message.photo:
                photo_bytes = await bot.download(message.photo[-1])
                response = model.generate_content([
                    "Ushbu rasmdagi matematik masalani tushuntirib yechib ber:", 
                    {"mime_type": "image/jpeg", "data": photo_bytes.getvalue()}
                ])
            else:
                response = model.generate_content(f"Ushbu matematik masalani tushuntirib yechib ber: {message.text}")
            
            users_db[user_id]['count'] += 1
            await msg.edit_text(f"📚 {message.from_user.first_name}, mana sen yuborgan masala javoblari:\n\n{response.text}\n\n✅ Masala @{bot.username} yordamida bajarildi.")
        except Exception:
            await msg.edit_text("😔 Kechirasiz, masalani yechishda xatolik yuz berdi. Iltimos rasm aniqroq bo'lsin yoki matnni tekshiring.")

    # 3. Video Yuklash
    elif state == 'video' and message.text:
        if "http" in message.text:
            await message.answer_photo(
                photo="https://picsum.photos/400/200", 
                caption=f"🎬 Video topildi!\n📝 Nomi: Video_{user_id}.mp4\n\nPastdagi tugmani bosing:",
                reply_markup=InlineKeyboardBuilder().button(text="📥 Yuklab olish", callback_data="download_video").as_markup()
            )
        else:
            await message.answer("❌ Iltimos, to'g'ri video linkini yuboring.")

    # 4. Murojat
    elif state == 'contact' and message.text:
        await bot.send_message(ADMIN_ID, f"📩 Yangi murojat!\nKimdan: {message.from_user.full_name}\nID: {user_id}\n\nMatn: {message.text}", 
                               reply_markup=InlineKeyboardBuilder().button(text="✍️ Javob berish", callback_data=f"reply_{user_id}").as_markup())
        await message.answer("✅ Murojatingiz adminga yuborildi. Tez orada javob olasiz!")
    
    # 5. Admin Javob berish holati
    elif state and state.startswith('replying_to_') and message.text:
        target_id = int(state.split('_')[-1])
        try:
            await bot.send_message(target_id, f"👨‍💻 Admin javobi:\n\n{message.text}")
            await message.answer("✅ Javobingiz yuborildi.")
            active_state[user_id] = None
        except Exception:
            await message.answer("❌ Xabarni yuborib bo'lmadi.")

# --- CALLBACKLAR ---
@dp.callback_query(F.data == "check")
async def check_callback(call: types.CallbackQuery):
    not_subbed = await check_sub(call.from_user.id)
    if not not_subbed:
        await call.message.delete()
        await call.message.answer("🎉 Tabriklayman! Endi botdan to'liq foydalanishingiz mumkin.", reply_markup=main_menu(call.from_user.id == ADMIN_ID))
    else:
        await call.answer("❌ Hali hamma kanallarga a'zo bo'lmadingiz!", show_alert=True)

@dp.callback_query(F.data.startswith("reply_"))
async def admin_reply_callback(call: types.CallbackQuery):
    target_id = call.data.split("_")[1]
    active_state[call.from_user.id] = f"replying_to_{target_id}"
    await call.message.answer(f"🆔 {target_id} ga javobingizni yozing:")
    await call.answer()

# --- ADMIN PANEL ---
@dp.message(F.text == "📊 Statistika")
async def show_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    total = len(users_db)
    top_users = sorted(users_db.items(), key=lambda x: x[1]['count'], reverse=True)[:3]
    text = f"📊 Bot statistikasi:\n👥 Jami foydalanuvchilar: {total}\n\n🏆 Top 3 faol foydalanuvchi:\n"
    for i, (uid, data) in enumerate(top_users, 1):
        text += f"{i}. {data['name']} - {data['count']} ta misol\n"
    await message.answer(text)

@dp.message(F.text == "📢 Post joylash")
async def post_start(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    active_state[ADMIN_ID] = 'broadcasting'
    await message.answer("Hohlagan post turini yuboring (Text, rasm, video). (FN) so'zi foydalanuvchi nomi bilan almashadi. 📢", reply_markup=back_kb())

@dp.message(F.content_type.in_({'text', 'photo', 'video'}))
async def do_broadcast(message: types.Message):
    if active_state.get(ADMIN_ID) != 'broadcasting': return
    if message.text == "🔙 Orqaga": return # Orqaga tugmasini o'tkazib yubormaslik uchun
    
    count = 0
    for user_id in users_db.keys():
        try:
            name = users_db[user_id]['name']
            if message.text:
                text = message.text.replace("(FN)", name)
                await bot.send_message(user_id, text)
            elif message.photo:
                caption = message.caption.replace("(FN)", name) if message.caption else ""
                await bot.send_photo(user_id, message.photo[-1].file_id, caption=caption)
            elif message.video:
                caption = message.caption.replace("(FN)", name) if message.caption else ""
                await bot.send_video(user_id, message.video.file_id, caption=caption)
            count += 1
        except Exception: pass
    
    await message.answer(f"✅ Post {count} kishiga yuborildi.", reply_markup=main_menu(True))
    active_state[ADMIN_ID] = None

# --- ASOSIY ISHGA TUSHIRISH ---
async def main():
    Thread(target=run_flask).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
    
