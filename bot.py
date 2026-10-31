import os
import shutil
import threading
import json
import telebot
import yt_dlp
import instaloader
from flask import Flask
from telebot import types

BOT_TOKEN = "8948057491:AAEfaBcEn-PczAIAELBlliohnHKIpINPNGA"
ADMIN_ID = 8886868325
USERS_FILE = "users_data.json"

bot = telebot.TeleBot(BOT_TOKEN)
DOWNLOAD_DIR = "downloads"
REQUIRED_CHANNEL = "" # اگر خواستید کانال بگذارید آیدی مثل @channel_username را اینجا قرار دهید

# ایجاد سرور وب کوچک برای جلوگیری از خطای پورت در رندر
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

# مدیریت پایدار کاربران (جلوگیری از پاک شدن با آپدیت)
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_user(message):
    users = load_users()
    user_id = str(message.from_user.id)
    user_data = {
        "id": message.from_user.id,
        "username": message.from_user.username or "ندارد",
        "first_name": message.from_user.first_name or "بدون نام"
    }
    if user_id not in users:
        users[user_id] = user_data
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=4)

L = instaloader.Instaloader(
    dirname_pattern=DOWNLOAD_DIR,
    download_videos=True,
    download_video_thumbnails=False,
    save_metadata=False,
    compress_json=False
)

def check_membership(user_id):
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except:
        pass
    return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    save_user(message)
    
    if REQUIRED_CHANNEL and not check_membership(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 عضويت در کانال", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("🔄 عضو شدم، بررسی مجدد", callback_data="check_sub"))
        bot.reply_to(message, f"⚠️ برای استفاده از ربات ابتدا باید در کانال ما عضو شوید:\n@{REQUIRED_CHANNEL}\n\nسپس روی دکمه‌ی زیر کلیک کنید.", reply_markup=markup)
        return

    markup = None
    if message.from_user.id == ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("📊 آمار کاربران"), types.KeyboardButton("📢 ارسال پیام همگانی"))

    bot.reply_to(
        message,
        "سلام! 🤖\n"
        "به ربات حرفه‌ای دانلود از اینستاگرام خوش آمدید.\n\n"
        "📌 **راهنمای استفاده:**\n"
        "1️⃣ لینک پست، ریلز یا استوری را بفرستید تا ویدیو/عکس + کپشن آن را دریافت کنید و دکمه استخراج صوت را داشته باشید.\n"
        "2️⃣ آیدی یک پیج عمومی را بفرستید تا آخرین پست‌های آن دریافت شوند.",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == "📊 آمار کاربران" and message.from_user.id == ADMIN_ID)
def admin_stats(message):
    users = load_users()
    total = len(users)
    text = f"📊 **تعداد کل کاربران ربات:** {total}\n\n👥 **لیست کاربران:**\n"
    for uid, info in list(users.items()[:30]): # نمایش ۳۰ کاربر آخر برای جلوگیری از طولانی شدن
        text += f"- نام: {info['first_name']} | یوزرنیم: @{info['username']} | آیدی: `{info['id']}`\n"
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📢 ارسال پیام همگانی" and message.from_user.id == ADMIN_ID)
def admin_broadcast_prompt(message):
    msg = bot.reply_to(message, "💬 لطفا متن پیام همگانی خود را بفرستید:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    users = load_users()
    success = 0
    failed = 0
    for uid in users.keys():
        try:
            bot.send_message(int(uid), message.text)
            success += 1
        except:
            failed += 1
    bot.reply_to(message, f"✅ پیام همگانی با موفقیت ارسال شد.\nرسیده به: {success}\nخطا/مسدودکرده: {failed}")

@bot.callback_query_handler(func=lambda call: call.data == "extract_audio")
def callback_extract_audio(call):
    try:
        bot.answer_callback_query(call.id, "🎵 در حال استخراج صدا...")
        # پیدا کردن فایل ویدیویی موجود در پوشه
        video_file = None
        for root, dirs, files in os.walk(DOWNLOAD_DIR):
            for file in files:
                if file.endswith('.mp4'):
                    video_file = os.path.join(root, file)
                    break
        
        if video_file and os.path.exists(video_file):
            audio_path = video_file.replace('.mp4', '.mp3')
            # استخراج صدا با yt-dlp یا ابزار داخلی
            os.system(f'ffmpeg -i "{video_file}" -q:a 0 -map a "{audio_path}" -y > /dev/null 2>&1')
            
            if os.path.exists(audio_path):
                with open(audio_path, 'rb') as audio:
                    bot.send_audio(call.message.chat.id, audio, caption="🎵 صوت استخراج شده توسط ربات")
            else:
                # روش جایگزین با yt-dlp اگر سیستم فایل صوتی نداشت
                bot.reply_to(call.message, "⚠️ امکان استخراج صوت برای این فایل مقدور نبود.")
        else:
            bot.reply_to(call.message, "⚠️ ویدیویی برای استخراج صدا یافت نشد.")
    except Exception as e:
        bot.reply_to(call.message, f"❌ خطا در استخراج صوت: {str(e)}")

@bot.message_handler(func=lambda message: True)
def handle_instagram_request(message):
    save_user(message)
    if REQUIRED_CHANNEL and not check_membership(message.from_user.id):
        bot.reply_to(message, "⚠️ لطفا ابتدا در کانال ربات عضو شوید تا بتوانید از امکانات آن استفاده کنید.")
        return

    text = message.text.strip()
    clear_downloads()
    
    if text.startswith("http://") or text.startswith("https://"):
        status_msg = bot.reply_to(message, "⏳ در حال دانلود ویدیو و استخراج اطلاعات...")
        try:
            ydl_opts = {
                'format': 'best',
                'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
                'quiet': True,
            }
            
            caption_text = ""
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=True)
                file_path = ydl.prepare_filename(info)
                caption_text = info.get('description', 'کپشنی یافت نشد.')

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🎵 استخراج صوت از این ویدیو", callback_data="extract_audio"))

            with open(file_path, 'rb') as video:
                bot.send_video(
                    message.chat.id, 
                    video, 
                    caption=f"✅ دانلود با موفقیت انجام شد.\n\n📝 **کپشن:**\n{caption_text[:800]}", 
                    parse_mode="Markdown",
                    reply_markup=markup
                )
            
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
                caption=f"👤 **{profile.username}**\n👥 فالوور: {profile.followers}\n📝 بیو: {profile.biography}",
                parse_mode="Markdown"
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
                                    bot.send_video(message.chat.id, f, caption="📥 پست دانلود شده")
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
    web_thread = threading.Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    
    print("Bot & Web server are running...")
    try:
        bot.remove_webhook()
    except:
        pass
    bot.infinity_polling()
