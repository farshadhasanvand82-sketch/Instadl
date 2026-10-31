import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
import yt_dlp

# تعریف توکن به صورت متغیر عمومی
BOT_TOKEN = "8948057491:AAEfaBcEn-PczAIAELBlliohnHKIpINPNGA"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "سلام! 🤖\n"
        "ابزار دانلودر اینستاگرام شما فعال و آماده به کار است.\n"
        "لینک پست، ریلز یا ویدیو را بفرستید تا دریافتش کنم."
    )

@dp.message()
async def download_handler(message: types.Message):
    url = message.text.strip()
    
    if url.startswith("http://") or url.startswith("https://"):
        status_msg = await message.answer("⏳ در حال پردازش و دانلود...")
        try:
            ydl_opts = {
                'format': 'best',
                'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
                'quiet': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
            
            video_file = FSInputFile(file_path)
            await message.answer_video(video_file, caption="✅ دانلود با موفقیت انجام شد.")
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
            await bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
            
        except Exception as e:
            await message.answer(f"❌ خطا در پردازش لینک:\n{str(e)}")
    else:
        await message.answer("لطفاً یک لینک معتبر ارسال کنید.")

async def main():
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
