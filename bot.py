import os
import shutil
import threading
import telebot
import yt_dlp
import instaloader
from flask import Flask

BOT_TOKEN = "8948057491:AAEfaBcEn-PczAIAELBlliohnHKIpINPNGA"
bot = telebot.TeleBot(BOT_TOKEN)

DOWNLOAD_DIR = "downloads"

# ایجاد سرور وب کوچک برای جلوگیری از خطای پورت در رندر (Web Service)
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Instagram Downloader Bot is running live!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# تابع ایجاد و پاکسازی پوشه دانلودها
def clear_downloads():
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

clear_downloads()

L = instaloader.Instaloader(
    dirname_pattern=DOWNLOAD_DIR,
    download_videos=True,
    download_video_thumbnails=False,
    save_metadata=False,
    compress_json=False
)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "سلام! 🤖\n"
        "ابزار دانلودر اینستاگرام (فعال و پایدار روی رندر) آماده است.\n\n"
        "📌 **راهنما:**\n"
        "1️⃣ لینک پست یا ریلز را بفرستید.\n"
        "2️⃣ آیدی یک پیج را بفرستید تا پست‌های آن را دریافت کنید."
    )

@bot.message_handler(func=lambda message: True)
def handle_instagram_request(message):
    text = message.text.strip()
    clear_downloads()
    
    if text.startswith("http://") or text.startswith("https://"):
        status_msg = bot.reply_to(message, "⏳ در حال دانلود و ارسال...")
        try:
            ydl_opts = {
                'format': 'best',
                'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
                'quiet': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=True)
                file_path = ydl.prepare_filename(info)
            
            with open(file_path, 'rb') as video:
                bot.send_video(message.chat.id, video, caption="✅ دانلود با موفقیت انجام شد.")
            
            bot.delete_message(message.chat.id, status_msg.message_id)
            
        except Exception as e:
            bot.reply_to(message, f"❌ خطا در دانلود لینک:\n{str(e)}")
            
        finally:
            clear_downloads()
            
    else:
        username = text.replace("@", "").strip()
        status_msg = bot.reply_to(message, f"⏳ در حال استخراج و دانلود پست‌های پیج `{username}`...")
        
        try:
            profile = instaloader.Profile.from_username(L.context, username)
            
            bot.send_photo(
                message.chat.id, 
                profile.profile_pic_url, 
                caption=f"👤 **{profile.username}**\n👥 فالوور: {profile.followers}\n📝 بیو: {profile.biography}"
            )
            
            count = 0
            for post in profile.get_posts():
                if count >= 3:
                    break
                L.download_post(post, target=username)
                count += 1
            
            sent_files = 0
            for root, dirs, files in os.walk(DOWNLOAD_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    if file.endswith(('.mp4', '.jpg', '.jpeg')):
                        try:
                            with open(file_path, 'rb') as f:
                                if file.endswith('.mp4'):
                                    bot.send_video(message.chat.id, f)
                                else:
                                    bot.send_photo(message.chat.id, f)
                            sent_files += 1
                        except:
                            pass
            
            if sent_files == 0:
                bot.reply_to(message, "⚠️ پستی برای دانلود یافت نشد یا پیج پرایویت است.")
                
            bot.delete_message(message.chat.id, status_msg.message_id)
            
        except Exception as e:
            bot.reply_to(message, f"❌ خطا در پردازش پیج:\n{str(e)}")
            
        finally:
            clear_downloads()

if __name__ == "__main__":
    # اجرای وب سرور در پس‌زمینه برای حفظ پورت رندر
    threading.Thread(target=run_web).load if hasattr(threading.Thread(target=run_web), 'load') else None
    web_thread = threading.Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    
    print("Bot & Web server are running...")
    bot.infinity_polling()
