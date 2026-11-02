import os
import shutil
import threading
import json
import telebot
import yt_dlp
from flask import Flask
from telebot import types

BOT_TOKEN = "8948057491:AAEfaBcEn-PczAIAELBlliohnHKIpINPNGA"
ADMIN_ID = 8886868325
USERS_FILE = "users_data.json"
SETTINGS_FILE = "settings.json"

bot = telebot.TeleBot(BOT_TOKEN)
DOWNLOAD_DIR = "downloads"

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Clean & Stable Multi-Downloader Bot is running live!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def clear_downloads():
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

clear_downloads()

def load_json(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default_val
    return default_val

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_users():
    return load_json(USERS_FILE, {})

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
        save_json(USERS_FILE, users)

def load_settings():
    return load_json(SETTINGS_FILE, {"channel": ""})

def save_settings(settings):
    save_json(SETTINGS_FILE, settings)

def check_membership(user_id):
    settings = load_settings()
    channel = settings.get("channel")
    if not channel:
        return True
    try:
        member = bot.get_chat_member(channel, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except:
        pass
    return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    save_user(message)
    settings = load_settings()
    channel = settings.get("channel")
    
    if channel and not check_membership(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 عضويت در کانال", url=f"https://t.me/{channel.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("🔄 عضو شدم، بررسی مجدد", callback_data="check_sub"))
        bot.reply_to(message, f"⚠️ برای استفاده از ربات ابتدا باید در کانال ما عضو شوید:\n{channel}\n\nسپس روی دکمه‌ی زیر کلیک کنید.", reply_markup=markup)
        return

    markup = None
    if message.from_user.id == ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("📊 آمار کاربران"), types.KeyboardButton("📢 ارسال پیام همگانی"))
        markup.add(types.KeyboardButton("⚙️ تنظیم کانال قفل"))

    bot.reply_to(
        message,
        "سلام! 🤖\n"
        "به ربات جامع دانلود رسانه خوش آمدید.\n\n"
        "📌 لینک خود را از پلتفرم‌های زیر بفرستید:\n"
        "📸 **اینستاگرام:** پست و ریلز\n"
        "▶️ **یوتیوب:** با انتخاب کیفیت دلخواه (زیر ۵۱۲ مگ)\n"
        "🎵 **اسپاتیفای و ساندکلود:** دریافت فایل صوتی باکیفیت",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check_sub(call):
    if check_membership(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ عضویت شما تایید شد!")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        send_welcome(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ شما هنوز در کانال عضو نشده‌اید!", show_alert=True)

@bot.message_handler(func=lambda message: message.text == "📊 آمار کاربران" and message.from_user.id == ADMIN_ID)
def admin_stats(message):
    users = load_users()
    settings = load_settings()
    total = len(users)
    channel = settings.get("channel") or "تنظیم نشده"
    text = f"📊 **تعداد کل کاربران ربات:** {total}\n📢 **کانال قفل فعلی:** {channel}\n\n👥 **آخرین کاربران:**\n"
    for uid, info in list(users.items())[-30:]:
        text += f"- {info['first_name']} | @{info['username']} | `{info['id']}`\n"
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
    bot.reply_to(message, f"✅ پیام همگانی ارسال شد.\nموفق: {success}\nناموفق: {failed}")

@bot.message_handler(func=lambda message: message.text == "⚙️ تنظیم کانال قفل" and message.from_user.id == ADMIN_ID)
def admin_set_channel(message):
    msg = bot.reply_to(message, "📢 لطفا آیدی کانال خود را با فرمت `@channel` بفرستید (برای غیرفعال کردن کلمه `off` را بفرستید):")
    bot.register_next_step_handler(msg, process_save_channel)

def process_save_channel(message):
    settings = load_settings()
    text = message.text.strip()
    if text.lower() == "off":
        settings["channel"] = ""
        save_settings(settings)
        bot.reply_to(message, "✅ قفل کانال با موفقیت غیرفعال شد.")
    else:
        if not text.startswith("@"):
            text = "@" + text
        settings["channel"] = text
        save_settings(settings)
        bot.reply_to(message, f"✅ کانال قفل با موفقیت روی `{text}` تنظیم شد.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("yt_"))
def callback_yt_download(call):
    try:
        data_parts = call.data.split("_")
        format_id = data_parts[1]
        url = "_".join(data_parts[2:])
        
        bot.answer_callback_query(call.id, "⏳ در حال دانلود ویدیو...")
        status_msg = bot.send_message(call.message.chat.id, "📥 در حال آماده‌سازی و ارسال ویدیو...")
        
        ydl_opts = {
            'format': f'{format_id}+bestaudio/best',
            'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
            'merge_output_format': 'mp4',
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            if not os.path.exists(file_path):
                file_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp4'
            
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path) / (1024 * 1024)
                if file_size > 512:
                    bot.reply_to(call.message, "❌ حجم ویدیو بیشتر از ۵۱۲ مگابایت است.")
                else:
                    with open(file_path, 'rb') as vid:
                        bot.send_video(call.message.chat.id, vid, caption="✅ دانلود ویدیو با موفقیت انجام شد.")
            else:
                bot.reply_to(call.message, "❌ خطا در آماده‌سازی فایل.")
                
        try:
            bot.delete_message(call.message.chat.id, status_msg.message_id)
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
            
    except Exception as e:
        bot.reply_to(call.message, f"❌ خطا در دانلود: {str(e)}")
    finally:
        clear_downloads()

@bot.message_handler(func=lambda message: True)
def handle_all_requests(message):
    save_user(message)
    settings = load_settings()
    channel = settings.get("channel")
    if channel and not check_membership(message.from_user.id):
        bot.reply_to(message, "⚠️ لطفا ابتدا در کانال ربات عضو شوید.")
        return

    text = message.text.strip()
    
    if not (text.startswith("http://") or text.startswith("https://")):
        bot.reply_to(message, "❌ لطفا یک لینک معتبر ارسال کنید.")
        return

    status_msg = bot.reply_to(message, "⏳ در حال پردازش هوشمند لینک...")
    
    try:
        # پردازش اینستاگرام و یوتیوب و موزیک به صورت ایمن
        if "instagram.com" in text:
            ydl_opts = {
                'format': 'best',
                'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=True)
                file_path = ydl.prepare_filename(info)
                if not os.path.exists(file_path):
                    file_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp4'
                caption_text = info.get('description') or "کپشنی یافت نشد."

            if os.path.exists(file_path):
                with open(file_path, 'rb') as vid:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("🔗 اشتراک‌گذاری", url=text))
                    bot.send_video(message.chat.id, vid, caption=f"✅ دانلود انجام شد.\n\n📝 کپشن:\n{caption_text[:800]}", reply_markup=markup)
                bot.delete_message(message.chat.id, status_msg.message_id)
            else:
                bot.edit_message_text("⚠️ فایلی برای این لینک یافت نشد.", message.chat.id, status_msg.message_id)
            return

        elif "youtube.com" in text or "youtu.be" in text:
            ydl_opts = {'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=False)
                formats = info.get('formats', [])
                
                markup = types.InlineKeyboardMarkup(row_width=2)
                added_resolutions = set()
                
                for f in formats:
                    if f.get('vcodec') != 'none' and f.get('height'):
                        res = f'{f.get("height")}p'
                        format_id = f.get('format_id')
                        if res not in added_resolutions and int(f.get('height')) <= 1080:
                            added_resolutions.add(res)
                            markup.add(types.InlineKeyboardButton(f"📥 کیفیت {res}", callback_data=f"yt_{format_id}_{text}"))
                
                bot.edit_message_text("🎬 کیفیت مورد نظر خود را انتخاب کنید:", message.chat.id, status_msg.message_id, reply_markup=markup)
            return

        elif "spotify.com" in text or "soundcloud.com" in text:
            bot.edit_message_text("🎧 در حال دریافت فایل صوتی...", message.chat.id, status_msg.message_id)
            
            # تبدیل لینک اسپاتیفای به جستجوی امن برای دور زدن کامل DRM
            search_query = text
            if "spotify.com" in text:
                try:
                    import urllib.request
                    req = urllib.request.Request(text, headers={'User-Agent': 'Mozilla/5.0'})
                    html = urllib.request.urlopen(req).read().decode('utf-8')
                    import re
                    m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                    if m:
                        search_query = f"ytsearch:{m.group(1)}"
                except:
                    search_query = f"ytsearch:{text}"

            ydl_opts = {
                'format': 'bestaudio',
                'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=True)
                if 'entries' in info:
                    info = info['entries'][0]
                file_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as audio:
                    bot.send_audio(message.chat.id, audio, caption="🎵 موزیک دانلود شده با موفقیت")
                bot.delete_message(message.chat.id, status_msg.message_id)
            else:
                bot.edit_message_text("❌ خطا در دانلود فایل صوتی.", message.chat.id, status_msg.message_id)
            return

        else:
            bot.edit_message_text("❌ لینک وارد شده پشتیبانی نمی‌شود.", message.chat.id, status_msg.message_id)

    except Exception as e:
        try:
            bot.edit_message_text(f"❌ خطا در پردازش درخواست: {str(e)}", message.chat.id, status_msg.message_id)
        except:
            pass
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
