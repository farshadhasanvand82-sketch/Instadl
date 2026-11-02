import os
import shutil
import threading
import json
import telebot
import yt_dlp
from PIL import Image, ImageDraw, ImageFont
from flask import Flask
from telebot import types

BOT_TOKEN = "8948057491:AAEfaBcEn-PczAIAELBlliohnHKIpINPNGA"
ADMIN_ID = 8886868325
USERS_FILE = "users_data.json"
SETTINGS_FILE = "settings.json"

bot = telebot.TeleBot(BOT_TOKEN)
DOWNLOAD_DIR = "downloads"

user_states = {}
cover_auth = {}
cover_data = {}

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 All-in-One Multi-Downloader & Cover Bot is running live!"

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

def get_main_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 اینستاگرام", callback_data="menu_insta"),
        types.InlineKeyboardButton("🎨 ساخت کاور", callback_data="menu_cover"),
        types.InlineKeyboardButton("🎵 اسپاتیفای / ساندکلود", callback_data="menu_music")
    )
    return markup

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

    admin_markup = None
    if message.from_user.id == ADMIN_ID:
        admin_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        admin_markup.add(types.KeyboardButton("📊 آمار کاربران"), types.KeyboardButton("📢 ارسال پیام همگانی"))
        admin_markup.add(types.KeyboardButton("⚙️ تنظیم کانال قفل"))

    bot.reply_to(
        message,
        "سلام! 🤖\n"
        "به ربات پیشرفته ساخت کاور و دانلود رسانه خوش آمدید.\n\n"
        "📌 **برای شروع، لطفاً گزینه مورد نظر خود را از دکمه‌های زیر انتخاب کنید:**",
        reply_markup=get_main_menu_markup()
    )
    if admin_markup:
        bot.send_message(message.chat.id, "🛠 پنل مدیریت:", reply_markup=admin_markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def callback_menu_selection(call):
    user_id = call.from_user.id
    action = call.data.replace("menu_", "")
    
    if action == "insta":
        user_states[user_id] = "waiting_insta"
        text = "📸 **بخش اینستاگرام فعال شد.**\n\nحالا لینک پست، ریلز یا عکس اینستاگرام خود را بفرستید:"
        markup = get_main_menu_markup()
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        except:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
            
    elif action == "cover":
        if cover_auth.get(user_id):
            user_states[user_id] = "waiting_cover_bg"
            cover_data[user_id] = {}
            text = "🎨 **بخش ساخت کاور فعال شد.**\n\n🖼 لطفاً **تصویر اول (بک‌گراند)** را به صورت عکس ارسال کنید:"
            markup = get_main_menu_markup()
            bot.answer_callback_query(call.id)
            try:
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
            except:
                bot.send_message(call.message.chat.id, text, reply_markup=markup)
        else:
            user_states[user_id] = "waiting_cover_password"
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "🔐 لطفا رمز عبور بخش ساخت کاور را وارد کنید:")

    elif action == "music":
        user_states[user_id] = "waiting_music"
        text = "🎵 **بخش موزیک فعال شد.**\n\nحالا لینک آهنگ اسپاتیفای یا ساندکلود خود را بفرستید:"
        markup = get_main_menu_markup()
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        except:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

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

@bot.message_handler(content_types=['photo', 'text'])
def handle_all_requests(message):
    user_id = message.from_user.id
    save_user(message)
    settings = load_settings()
    channel = settings.get("channel")
    if channel and not check_membership(user_id):
        bot.reply_to(message, "⚠️ لطفا ابتدا در کانال ربات عضو شوید.")
        return

    current_state = user_states.get(user_id)
    text = message.text.strip() if message.text else ""

    # بررسی رمز ساخت کاور
    if current_state == "waiting_cover_password":
        if text == "negin":
            cover_auth[user_id] = True
            user_states[user_id] = "waiting_cover_bg"
            cover_data[user_id] = {}
            bot.reply_to(message, "✅ رمز تایید شد!\n\n🖼 لطفاً **تصویر اول (بک‌گراند)** را به صورت عکس بفرستید:", reply_markup=get_main_menu_markup())
        else:
            bot.reply_to(message, "❌ رمز اشتباه است. دوباره تلاش کنید:", reply_markup=get_main_menu_markup())
        return

    # دریافت تصویر اول کاور
    if current_state == "waiting_cover_bg":
        if message.photo:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            bg_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_bg.jpg")
            with open(bg_path, 'wb') as new_file:
                new_file.write(downloaded_file)
            
            cover_data[user_id]["bg"] = bg_path
            user_states[user_id] = "waiting_cover_logo"
            bot.reply_to(message, "✅ تصویر بک‌گراند ذخیره شد.\n\n🖼 حالا **تصویر دوم (لوگوی اسم فیلم به صورت PNG شفاف)** را بفرستید:")
        else:
            bot.reply_to(message, "❌ لطفاً تصویر بک‌گراند را به صورت عکس ارسال کنید.")
        return

    # دریافت تصویر دوم کاور (لوگو)
    if current_state == "waiting_cover_logo":
        if message.photo:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            logo_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_logo.png")
            with open(logo_path, 'wb') as new_file:
                new_file.write(downloaded_file)
            
            cover_data[user_id]["logo"] = logo_path
            user_states[user_id] = "waiting_cover_subtitle"
            bot.reply_to(message, "✅ لوگو ذخیره شد.\n\n💬 حالا **متن اول (مثل: زیرنویس فارسی بدون سانسور یا دوبله فارسی)** را بفرستید:")
        else:
            bot.reply_to(message, "❌ لطفاً لوگو را به صورت عکس ارسال کنید.")
        return

    # دریافت متن اول و ساخت نهایی تصویر کاور
    if current_state == "waiting_cover_subtitle":
        if text:
            subtitle_text = text
            bg_path = cover_data[user_id].get("bg")
            logo_path = cover_data[user_id].get("logo")

            status_msg = bot.reply_to(message, "🎨 در حال ساخت و ترکیب کاور حرفه‌ای...")

            try:
                bg = Image.open(bg_path).convert("RGBA")
                logo = Image.open(logo_path).convert("RGBA")

                base_width = 1280
                w_percent = (base_width / float(bg.size[0]))
                h_size = int(float(bg.size[1]) * float(w_percent))
                bg = bg.resize((base_width, h_size), Image.Resampling.LANCZOS)

                draw = ImageDraw.Draw(bg)
                
                try:
                    font_netflix = ImageFont.truetype("arial.ttf", 45)
                    font_sub = ImageFont.truetype("arial.ttf", 36)
                except:
                    font_netflix = ImageFont.load_default()
                    font_sub = ImageFont.load_default()

                final_logo_x = 80
                final_logo_y = int(bg.size[1] * 0.45)
                
                logo_w = int(bg.size[0] * 0.35)
                logo_h = int(logo.size[1] * (logo_w / logo.size[0]))
                logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
                
                bg.paste(logo, (final_logo_x, final_logo_y), logo)

                draw.text((final_logo_x, final_logo_y - 60), "NETFLIXSIT1", fill=(0, 220, 220), font=font_netflix)

                text_x = 80
                text_y = final_logo_y + logo_h + 30
                
                draw.text((text_x, text_y), subtitle_text, fill=(255, 255, 255), font=font_sub)
                draw.text((text_x, text_y + 45), "دانلود شده از چنل نتفلیکس سایت", fill=(0, 220, 220), font=font_sub)

                output_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_output.jpg")
                bg.convert("RGB").save(output_path, "JPEG", quality=95)

                with open(output_path, 'rb') as photo:
                    bot.send_photo(message.chat.id, photo, caption="✅ کاور شما با موفقیت ساخته شد!\n🤖 t.me/zeucdl_bot", reply_markup=get_main_menu_markup())
                
                bot.delete_message(message.chat.id, status_msg.message_id)
            except Exception as e:
                bot.edit_message_text(f"❌ خطا در ساخت کاور: {str(e)}", message.chat.id, status_msg.message_id)

            user_states.pop(user_id, None)
            cover_data.pop(user_id, None)
        else:
            bot.reply_to(message, "❌ لطفاً متن زیرنویس یا دوبله را ارسال کنید.")
        return

    # بررسی اینکه آیا ورودی لینک معتبر است یا خیر
    if not (text.startswith("http://") or text.startswith("https://")):
        bot.reply_to(message, "❌ لطفا ابتدا یکی از دکمه‌های منوی زیر را انتخاب کنید و سپس لینک بفرستید:", reply_markup=get_main_menu_markup())
        return

    status_msg = bot.reply_to(message, "⏳ در حال پردازش لینک...")
    
    try:
        # پردازش اینستاگرام
        if current_state == "waiting_insta" or "instagram.com" in text:
            ydl_opts = {
                'format': 'best',
                'outtmpl': f'{DOWNLOAD_DIR}/t.me_zeucdl_bot_%(id)s.%(ext)s',
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
                    bot.send_video(message.chat.id, vid, caption=f"✅ دانلود انجام شد.\n\n📝 کپشن:\n{caption_text[:800]}\n\n🤖 t.me/zeucdl_bot", reply_markup=markup)
                bot.delete_message(message.chat.id, status_msg.message_id)
                bot.send_message(message.chat.id, "👇 برای دانلود بیشتر، یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=get_main_menu_markup())
            else:
                bot.edit_message_text("⚠️ فایلی برای این لینک یافت نشد.", message.chat.id, status_msg.message_id)
            user_states.pop(user_id, None)
            return

        # پردازش موزیک (اسپاتیفای / ساندکلود)
        elif current_state == "waiting_music" or "spotify.com" in text or "soundcloud.com" in text:
            bot.edit_message_text("🎧 در حال دریافت فایل صوتی...", message.chat.id, status_msg.message_id)
            
            target_url = text
            if "spotify.com" in text:
                try:
                    import urllib.request
                    req = urllib.request.Request(text, headers={'User-Agent': 'Mozilla/5.0'})
                    html = urllib.request.urlopen(req).read().decode('utf-8')
                    import re
                    m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                    if m:
                        target_url = f"scsearch:{m.group(1)}"
                except:
                    target_url = text

            ydl_opts = {
                'format': 'bestaudio',
                'outtmpl': f'{DOWNLOAD_DIR}/t.me_zeucdl_bot_%(id)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'noplaylist': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=True)
                if 'entries' in info:
                    info = info['entries'][0]
                file_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as audio:
                    bot.send_audio(message.chat.id, audio, caption="🎵 موزیک دانلود شده با موفقیت\n🤖 t.me/zeucdl_bot")
                bot.delete_message(message.chat.id, status_msg.message_id)
                bot.send_message(message.chat.id, "👇 برای دانلود بیشتر، یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=get_main_menu_markup())
            else:
                bot.edit_message_text("❌ خطا در دانلود فایل صوتی.", message.chat.id, status_msg.message_id)
            user_states.pop(user_id, None)
            return

        else:
            bot.edit_message_text("❌ لطفا ابتدا یکی از دکمه‌های منو را انتخاب کنید:", message.chat.id, status_msg.message_id, reply_markup=get_main_menu_markup())

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
