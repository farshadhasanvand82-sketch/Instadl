import os
import telebot
import yt_dlp

BOT_TOKEN = "8948057491:AAEfaBcEn-PczAIAELBlliohnHKIpINPNGA"
bot = telebot.TeleBot(BOT_TOKEN)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "سلام! 🤖\n"
        "ابزار دانلودر اینستاگرام شما فعال و آماده به کار است.\n"
        "لینک پست، ریلز یا ویدیو را بفرستید تا دریافتش کنم."
    )

@bot.message_handler(func=lambda message: True)
def download_handler(message):
    url = message.text.strip()
    
    if url.startswith("http://") or url.startswith("https://"):
        status_msg = bot.reply_to(message, "⏳ در حال پردازش و دانلود...")
        try:
            ydl_opts = {
                'format': 'best',
                'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
                'quiet': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
            
            with open(file_path, 'rb') as video:
                bot.send_video(message.chat.id, video, caption="✅ دانلود با موفقیت انجام شد.")
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
            bot.delete_message(message.chat.id, status_msg.message_id)
            
        except Exception as e:
            bot.reply_to(message, f"❌ خطا در پردازش لینک:\n{str(e)}")
    else:
        bot.reply_to(message, "لطفاً یک لینک معتبر ارسال کنید.")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
