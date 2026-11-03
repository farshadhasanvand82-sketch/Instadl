import os
import shutil
import threading
import json
import telebot
import yt_dlp
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
from flask import Flask
from telebot import types

BOT_TOKEN = "8948057491:AAEfaBcEn-PczAIAELBlliohnHKIpINPNGA"
ADMIN_IDS = [8886868325, 8250289921] # لیست ادمین‌ها
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
    return "🤖 Professional Multi-Downloader & Admin Bot is running live!"

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
        "first_name": message.from_user.first_name or "بدون نام",
        "banned": False
    }
    if user_id not in users:
        users[user_id] = user_data
    else:
        users[user_id]["first_name"] = message.from_user.first_name or "بدون نام"
        users[user_id]["username"] = message.from_user.username or "ندارد"
    save_json(USERS_FILE, users)

def is_banned(user_id):
    users = load_users()
    return users.get(str(user_id), {}).get("banned", False)

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

def get_main_menu_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 دانلود اینستاگرام", callback_data="menu_insta"),
        types.InlineKeyboardButton("🎵 دانلود اسپاتیفای/ساندکلود", callback_data="menu_music"),
        types.InlineKeyboardButton("🎨 ساخت کاور", callback_data="menu_cover")
    )
    if user_id in ADMIN_IDS:
        markup.add(types.InlineKeyboardButton("⚙️ پنل مدیریت پیشرفته", callback_data="menu_admin"))
    return markup

def get_admin_panel_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 آمار کاربران", callback_data="adm_stats"),
        types.InlineKeyboardButton("📢 ارسال همگانی", callback_data="adm_broadcast"),
        types.InlineKeyboardButton("📢 تنظیم کانال قفل", callback_data="adm_channel"),
        types.InlineKeyboardButton("🚫 مسدود/آزاد کردن کاربر", callback_data="adm_ban"),
        types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="adm_back")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        return
    save_user(message)
    settings = load_settings()
    channel = settings.get("channel")
    
    if channel and not check_membership(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 عضويت در کانال", url=f"https://t.me/{channel.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("🔄 عضو شدم، بررسی مجدد", callback_data="check_sub"))
        bot.reply_to(message, f"⚠️ برای استفاده از ربات ابتدا باید در کانال ما عضو شوید:\n{channel}\n\nسپس روی دکمه‌ی زیر کلیک کنید.", reply_markup=markup)
        return

    bot.reply_to(
        message,
        "سلام! 🤖\n"
        "به ربات پیشرفته ساخت کاور و دانلود رسانه خوش آمدید.\n\n"
        "📌 **برای شروع، لطفاً گزینه مورد نظر خود را از دکمه‌های زیر انتخاب کنید:**",
        reply_markup=get_main_menu_markup(user_id)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_") or call.data.startswith("adm_"))
def callback_router(call):
    user_id = call.from_user.id
    data = call.data

    if is_banned(user_id):
        bot.answer_callback_query(call.id, "❌ شما توسط ادمین مسدود شده‌اید.", show_alert=True)
        return

    if data == "menu_insta":
        user_states[user_id] = "waiting_insta"
        text = "📸 **بخش اینستاگرام فعال شد.**\n\nحالا لینک پست، ریلز یا عکس اینستاگرام خود را بفرستید:"
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_main_menu_markup(user_id))
        except:
            bot.send_message(call.message.chat.id, text, reply_markup=get_main_menu_markup(user_id))

    elif data == "menu_cover":
        if cover_auth.get(user_id):
            user_states[user_id] = "waiting_cover_bg"
            cover_data[user_id] = {}
            text = "🎨 **بخش ساخت کاور فعال شد.**\n\n🖼 لطفاً **تصویر اول (بک‌گراند)** را ارسال کنید:"
            bot.answer_callback_query(call.id)
            try:
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_main_menu_markup(user_id))
            except:
                bot.send_message(call.message.chat.id, text, reply_markup=get_main_menu_markup(user_id))
        else:
            user_states[user_id] = "waiting_cover_password"
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "🔐 لطفا رمز عبور بخش ساخت کاور را وارد کنید:")

    elif data == "menu_music":
        user_states[user_id] = "waiting_music"
        text = "🎵 **بخش موزیک فعال شد.**\n\nحالا لینک آهنگ اسپاتیفای یا ساندکلود خود را بفرستید:"
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_main_menu_markup(user_id))
        except:
            bot.send_message(call.message.chat.id, text, reply_markup=get_main_menu_markup(user_id))

    elif data == "menu_admin":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ دسترسی غیرمجاز!", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        bot.edit_message_text("🛠 **پنل مدیریت پیشرفته ربات**\n\nگزینه مورد نظر را انتخاب کنید:", call.message.chat.id, call.message.message_id, reply_markup=get_admin_panel_markup())

    elif data == "adm_stats":
        if user_id not in ADMIN_IDS: return
        users = load_users()
        settings = load_settings()
        total = len(users)
        banned_count = sum(1 for u in users.values() if u.get("banned"))
        channel = settings.get("channel") or "تنظیم نشده"
        text = f"📊 **آمار ربات:**\n\n👥 کل کاربران: {total}\n🚫 کاربران مسدود: {banned_count}\n📢 کانال قفل: {channel}"
        bot.answer_callback_query(call.id)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_admin_panel_markup())

    elif data == "adm_broadcast":
        if user_id not in ADMIN_IDS: return
        user_states[user_id] = "waiting_broadcast_text"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "💬 متن پیام همگانی خود را ارسال کنید:")

    elif data == "adm_channel":
        if user_id not in ADMIN_IDS: return
        user_states[user_id] = "waiting_channel_id"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📢 آیدی کانال را با فرمت `@channel` بفرستید (برای غیرفعال کردن `off` بفرستید):")

    elif data == "adm_ban":
        if user_id not in ADMIN_IDS: return
        user_states[user_id] = "waiting_ban_user"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🚫 آیدی عددی کاربر را برای مسدود/آزاد کردن بفرستید:")

    elif data == "adm_back":
        if user_id not in ADMIN_IDS: return
        bot.answer_callback_query(call.id)
        bot.edit_message_text("📌 **برای شروع، لطفاً گزینه مورد نظر خود را از دکمه‌های زیر انتخاب کنید:**", call.message.chat.id, call.message.message_id, reply_markup=get_main_menu_markup(user_id))

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

@bot.message_handler(content_types=['photo', 'document', 'text'])
def handle_all_requests(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        return
    save_user(message)
    settings = load_settings()
    channel = settings.get("channel")
    if channel and not check_membership(user_id):
        bot.reply_to(message, "⚠️ لطفا ابتدا در کانال ربات عضو شوید.")
        return

    current_state = user_states.get(user_id)
    text = message.text.strip() if message.text else ""

    # مدیریت پنل ادمین
    if user_id in ADMIN_IDS:
        if current_state == "waiting_broadcast_text":
            users = load_users()
            success = 0
            failed = 0
            for uid in users.keys():
                try:
                    bot.send_message(int(uid), text)
                    success += 1
                except:
                    failed += 1
            bot.reply_to(message, f"✅ پیام همگانی ارسال شد.\nموفق: {success}\nناموفق: {failed}")
            user_states.pop(user_id, None)
            return

        elif current_state == "waiting_channel_id":
            if text.lower() == "off":
                settings["channel"] = ""
                save_settings(settings)
                bot.reply_to(message, "✅ قفل کانال غیرفعال شد.")
            else:
                if not text.startswith("@"): text = "@" + text
                settings["channel"] = text
                save_settings(settings)
                bot.reply_to(message, f"✅ کانال قفل روی `{text}` تنظیم شد.")
            user_states.pop(user_id, None)
            return

        elif current_state == "waiting_ban_user":
            try:
                target_id = str(int(text))
                users = load_users()
                if target_id in users:
                    current_status = users[target_id].get("banned", False)
                    users[target_id]["banned"] = not current_status
                    save_json(USERS_FILE, users)
                    status_str = "مسدود شد 🚫" if users[target_id]["banned"] else "آزاد شد ✅"
                    bot.reply_to(message, f"کاربر `{target_id}` با موفقیت {status_str}")
                else:
                    bot.reply_to(message, "❌ کاربری با این آیدی در دیتابیس یافت نشد.")
            except:
                bot.reply_to(message, "❌ آیدی عددی نامعتبر است.")
            user_states.pop(user_id, None)
            return

    # بررسی رمز ساخت کاور
    if current_state == "waiting_cover_password":
        if text == "negin":
            cover_auth[user_id] = True
            user_states[user_id] = "waiting_cover_bg"
            cover_data[user_id] = {}
            bot.reply_to(message, "✅ رمز تایید شد!\n\n🖼 لطفاً **تصویر اول (بک‌گراند)** را ارسال کنید:", reply_markup=get_main_menu_markup(user_id))
        else:
            bot.reply_to(message, "❌ رمز اشتباه است. دوباره تلاش کنید:", reply_markup=get_main_menu_markup(user_id))
        return

    # دریافت تصویر اول کاور
    if current_state == "waiting_cover_bg":
        file_id = None
        if message.photo: file_id = message.photo[-1].file_id
        elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'): file_id = message.document.file_id

        if file_id:
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            bg_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_bg.jpg")
            with open(bg_path, 'wb') as new_file: new_file.write(downloaded_file)
            cover_data[user_id]["bg"] = bg_path
            user_states[user_id] = "waiting_cover_logo"
            bot.reply_to(message, "✅ تصویر بک‌گراند ذخیره شد.\n\n🖼 حالا **تصویر دوم (لوگوی اسم فیلم PNG)** را بفرستید:")
        else:
            bot.reply_to(message, "❌ لطفاً تصویر بک‌گراند را به صورت عکس یا فایل تصویری ارسال کنید.")
        return

    # دریافت تصویر دوم کاور
    if current_state == "waiting_cover_logo":
        file_id = None
        if message.photo: file_id = message.photo[-1].file_id
        elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'): file_id = message.document.file_id

        if file_id:
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            logo_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_logo.png")
            with open(logo_path, 'wb') as new_file: new_file.write(downloaded_file)
            cover_data[user_id]["logo"] = logo_path
            user_states[user_id] = "waiting_cover_subtitle"
            bot.reply_to(message, "✅ لوگو ذخیره شد.\n\n💬 حالا **متن اول (مثل: زیرنویس فارسی بدون سانسور)** را بفرستید:")
        else:
            bot.reply_to(message, "❌ لطفاً لوگو را به صورت عکس یا فایل تصویری ارسال کنید.")
        return

    # ساخت نهایی کاور با اصلاح کامل و بدون خطای متن فارسی
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

                font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                if not os.path.exists(font_path): font_path = "arial.ttf"

                try:
                    font_netflix = ImageFont.truetype(font_path, 42)
                    font_sub = ImageFont.truetype(font_path, 34)
                except:
                    font_netflix = ImageFont.load_default()
                    font_sub = ImageFont.load_default()

                final_logo_x = 70
                final_logo_y = int(bg.size[1] * 0.42)
                logo_w = int(bg.size[0] * 0.38)
                logo_h = int(logo.size[1] * (logo_w / logo.size[0]))
                logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
                bg.paste(logo, (final_logo_x, final_logo_y), logo)

                def draw_fixed_persian_text(draw_obj, xy, text_str, font_obj, text_color):
                    x, y = xy
                    # اصلاح هوشمند جهت برای رفع مشکل جدانویسی و برعکس بودن حروف فارسی
                    reshaped_text = arabic_reshaper.reshape(text_str)
                    bidi_text = get_display(reshaped_text)
                    
                    shadow_color = (0, 0, 0, 255)
                    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, 3), (3, 0)]:
                        draw_obj.text((x + dx, y + dy), bidi_text, fill=shadow_color, font=font_obj)
                    draw_obj.text((x, y), bidi_text, fill=text_color, font=font_obj)

                draw.text((final_logo_x, final_logo_y - 50), "NETFLIXSIT1", fill=(0, 220, 220, 255), font=font_netflix)

                text_x = 70
                text_y = final_logo_y + logo_h + 30
                
                draw_fixed_persian_text(draw, (text_x, text_y), subtitle_text, font_sub, (255, 255, 255, 255))
                draw_fixed_persian_text(draw, (text_x, text_y + 45), "دانلود شده از چنل نتفلیکس سایت", font_sub, (255, 255, 255, 255))

                output_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_output.jpg")
                bg.convert("RGB").save(output_path, "JPEG", quality=95)

                with open(output_path, 'rb') as photo:
                    bot.send_photo(message.chat.id, photo, caption="✅ کاور شما با موفقیت ساخته شد!\n🤖 t.me/zeucdl_bot", reply_markup=get_main_menu_markup(user_id))
                
                bot.delete_message(message.chat.id, status_msg.message_id)
            except Exception as e:
                bot.edit_message_text(f"❌ خطا در ساخت کاور: {str(e)}", message.chat.id, status_msg.message_id)

            user_states.pop(user_id, None)
            cover_data.pop(user_id, None)
        else:
            bot.reply_to(message, "❌ لطفاً متن زیرنویس یا دوبله را ارسال کنید.")
        return

    if not (text.startswith("http://") or text.startswith("https://")):
        bot.reply_to(message, "❌ لطفا ابتدا یکی از دکمه‌های منو را انتخاب کنید و سپس لینک بفرستید:", reply_markup=get_main_menu_markup(user_id))
        return

    status_msg = bot.reply_to(message, "⏳ در حال پردازش لینک...")
    
    try:
        if current_state == "waiting_insta" or "instagram.com" in text:
            ydl_opts = {'format': 'best', 'outtmpl': f'{DOWNLOAD_DIR}/t.me_zeucdl_bot_%(id)s.%(ext)s', 'quiet': True}
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
                bot.send_message(message.chat.id, "👇 برای دانلود بیشتر، گزینه مورد نظر را انتخاب کنید:", reply_markup=get_main_menu_markup(user_id))
            else:
                bot.edit_message_text("⚠️ فایلی برای این لینک یافت نشد.", message.chat.id, status_msg.message_id)
            user_states.pop(user_id, None)
            return

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
                    if m: target_url = f"scsearch:{m.group(1)}"
                except:
                    target_url = text

            ydl_opts = {
                'format': 'bestaudio',
                'outtmpl': f'{DOWNLOAD_DIR}/t.me_zeucdl_bot_%(id)s.%(ext)s',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                'quiet': True, 'noplaylist': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=True)
                if 'entries' in info: info = info['entries'][0]
                file_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as audio:
                    bot.send_audio(message.chat.id, audio, caption="🎵 موزیک دانلود شده با موفقیت\n🤖 t.me/zeucdl_bot")
                bot.delete_message(message.chat.id, status_msg.message_id)
                bot.send_message(message.chat.id, "👇 برای دانلود بیشتر، گزینه مورد نظر را انتخاب کنید:", reply_markup=get_main_menu_markup(user_id))
            else:
                bot.edit_message_text("❌ خطا در دانلود فایل صوتی.", message.chat.id, status_msg.message_id)
            user_states.pop(user_id, None)
            return

        else:
            bot.edit_message_text("❌ لطفا ابتدا یکی از دکمه‌های منو را انتخاب کنید:", message.chat.id, status_msg.message_id, reply_markup=get_main_menu_markup(user_id))

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
    try: bot.remove_webhook()
    except: pass
    bot.infinity_polling()
