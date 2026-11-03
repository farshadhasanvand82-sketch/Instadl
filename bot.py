import os
import shutil
import threading
import json
import telebot
import yt_dlp
from flask import Flask
from telebot import types

BOT_TOKEN = "8948057491:AAEfaBcEn-PczAIAELBlliohnHKIpINPNGA"
INITIAL_ADMINS = [8886868325, 8250289921]

USERS_FILE = "users_data.json"
SETTINGS_FILE = "settings.json"

bot = telebot.TeleBot(BOT_TOKEN)
DOWNLOAD_DIR = "downloads"

user_states = {}

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
        save_json(USERS_FILE, users)

def is_banned(user_id):
    users = load_users()
    return users.get(str(user_id), {}).get("banned", False)

def load_settings():
    default_settings = {
        "channels": [],
        "admins": INITIAL_ADMINS,
        "btn_names": {
            "insta": "📸 دانلود اینستاگرام",
            "music": "🎵 دانلود اسپاتیفای/ساندکلود"
        },
        "btn_order": ["insta", "music"]
    }
    data = load_json(SETTINGS_FILE, default_settings)
    if "channels" not in data: data["channels"] = []
    if "admins" not in data: data["admins"] = INITIAL_ADMINS
    if "btn_names" not in data: data["btn_names"] = default_settings["btn_names"]
    if "btn_order" not in data: data["btn_order"] = default_settings["btn_order"]
    return data

def save_settings(settings):
    save_json(SETTINGS_FILE, settings)

def check_membership(user_id):
    settings = load_settings()
    channels = settings.get("channels", [])
    if not channels:
        return True
    for ch in channels:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status in ['member', 'administrator', 'creator']:
                return True
        except:
            pass
    return False

def get_main_menu_markup(user_id):
    settings = load_settings()
    btn_names = settings.get("btn_names", {})
    btn_order = settings.get("btn_order", ["insta", "music"])
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for key in btn_order:
        if key == "insta":
            buttons.append(types.InlineKeyboardButton(btn_names.get("insta", "📸 دانلود اینستاگرام"), callback_data="menu_insta"))
        elif key == "music":
            buttons.append(types.InlineKeyboardButton(btn_names.get("music", "🎵 دانلود اسپاتیفای/ساندکلود"), callback_data="menu_music"))
            
    markup.add(*buttons)
    if user_id in settings.get("admins", INITIAL_ADMINS):
        markup.add(types.InlineKeyboardButton("⚙️ پنل مدیریت پیشرفته", callback_data="menu_admin"))
    return markup

def get_admin_panel_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 آمار کاربران", callback_data="adm_stats"),
        types.InlineKeyboardButton("📢 ارسال همگانی", callback_data="adm_broadcast"),
        types.InlineKeyboardButton("📢 مدیریت کانال‌های قفل", callback_data="adm_channels_mgmt"),
        types.InlineKeyboardButton("👥 مدیریت کاربران و ادمین‌ها", callback_data="adm_users_mgmt"),
        types.InlineKeyboardButton("🎛 مدیریت و تغییر نام دکمه‌ها", callback_data="adm_buttons_mgmt"),
        types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="adm_back")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if is_banned(user_id): return
    save_user(message)
    settings = load_settings()
    channels = settings.get("channels", [])
    
    if channels and not check_membership(user_id):
        markup = types.InlineKeyboardMarkup()
        for ch in channels:
            markup.add(types.InlineKeyboardButton(f"📢 عضويت در {ch}", url=f"https://t.me/{ch.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("🔄 عضو شدم، بررسی مجدد", callback_data="check_sub"))
        bot.reply_to(message, "⚠️ برای استفاده از ربات ابتدا باید در کانال‌های زیر عضو شوید:", reply_markup=markup)
        return

    bot.reply_to(
        message,
        "سلام! 🤖\nبه ربات پیشرفته دانلود رسانه خوش آمدید.\n\n📌 **گزینه مورد نظر خود را انتخاب کنید:**",
        reply_markup=get_main_menu_markup(user_id)
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_router(call):
    user_id = call.from_user.id
    data = call.data
    settings = load_settings()
    admins = settings.get("admins", INITIAL_ADMINS)

    if is_banned(user_id):
        bot.answer_callback_query(call.id, "❌ شما مسدود شده‌اید.", show_alert=True)
        return

    if data == "menu_insta":
        user_states[user_id] = "waiting_insta"
        bot.answer_callback_query(call.id)
        bot.edit_message_text("📸 **بخش اینستاگرام فعال شد.**\n\nلینک پست یا ریلز را بفرستید:", call.message.chat.id, call.message.message_id, reply_markup=get_main_menu_markup(user_id))

    elif data == "menu_music":
        user_states[user_id] = "waiting_music"
        bot.answer_callback_query(call.id)
        bot.edit_message_text("🎵 **بخش موزیک فعال شد.**\n\nلینک آهنگ را بفرستید:", call.message.chat.id, call.message.message_id, reply_markup=get_main_menu_markup(user_id))

    elif data == "menu_admin":
        if user_id not in admins:
            bot.answer_callback_query(call.id, "❌ دسترسی غیرمجاز!", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        bot.edit_message_text("🛠 **پنل مدیریت پیشرفته ربات**", call.message.chat.id, call.message.message_id, reply_markup=get_admin_panel_markup())

    elif data == "adm_stats":
        if user_id not in admins: return
        users = load_users()
        total = len(users)
        banned = sum(1 for u in users.values() if u.get("banned"))
        ch_list = ", ".join(settings.get("channels", [])) or "ندارد"
        text = f"📊 **آمار ربات:**\n\n👥 کل کاربران: {total}\n🚫 مسدود شده‌ها: {banned}\n📢 کانال‌های قفل: {ch_list}"
        bot.answer_callback_query(call.id)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_admin_panel_markup())

    elif data == "adm_broadcast":
        if user_id not in admins: return
        user_states[user_id] = "waiting_broadcast"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "💬 متن پیام همگانی را بفرستید:")

    elif data == "adm_channels_mgmt":
        if user_id not in admins: return
        ch_list = "\n".join([f"- {c}" for c in settings.get("channels", [])]) or "هیچ کانالی ثبت نشده است."
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("➕ افزودن کانال", callback_data="adm_add_ch"),
            types.InlineKeyboardButton("➖ حذف کانال", callback_data="adm_remove_ch"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="menu_admin")
        )
        bot.answer_callback_query(call.id)
        bot.edit_message_text(f"📢 **مدیریت کانال‌های قفل جوین اجباری:**\n\n{ch_list}", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "adm_add_ch":
        if user_id not in admins: return
        user_states[user_id] = "waiting_add_channel"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📢 آیدی کانال را بفرستید (مثل `@channel`):")

    elif data == "adm_remove_ch":
        if user_id not in admins: return
        user_states[user_id] = "waiting_remove_channel"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🗑 آیدی کانالی که می‌خواهید حذف شود را بفرستید:")

    elif data == "adm_users_mgmt":
        if user_id not in admins: return
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🚫 مسدود/آزاد کردن کاربر", callback_data="adm_ban_user"),
            types.InlineKeyboardButton("✉️ ارسال پیام به کاربر", callback_data="adm_msg_user"),
            types.InlineKeyboardButton("➕ افزودن ادمین جدید", callback_data="adm_add_admin"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="menu_admin")
        )
        bot.answer_callback_query(call.id)
        bot.edit_message_text("👥 **بخش مدیریت کاربران و ادمین‌ها:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "adm_ban_user":
        if user_id not in admins: return
        user_states[user_id] = "waiting_ban_input"
        bot.answer_callback_query(call.id)
        bot.send_message(message=call.message, text="🚫 آیدی عددی کاربر را برای مسدود/آزاد کردن بفرستید:")

    elif data == "adm_msg_user":
        if user_id not in admins: return
        user_states[user_id] = "waiting_user_msg_id"
        bot.answer_callback_query(call.id)
        bot.send_message(message=call.message, text="✉️ ابتدا آیدی عددی کاربر را بفرستید:")

    elif data == "adm_add_admin":
        if user_id not in admins: return
        user_states[user_id] = "waiting_new_admin_id"
        bot.answer_callback_query(call.id)
        bot.send_message(message=call.message, text="➕ آیدی عددی کاربر جدید را برای ادمین شدن بفرستید:")

    elif data == "adm_buttons_mgmt":
        if user_id not in admins: return
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✏️ تغییر نام دکمه‌ها", callback_data="adm_rename_btn"),
            types.InlineKeyboardButton("🔀 جابجایی ترتیب دکمه‌ها", callback_data="adm_move_btn"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="menu_admin")
        )
        bot.answer_callback_query(call.id)
        bot.edit_message_text("🎛 **مدیریت دکمه‌های منو:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "adm_rename_btn":
        if user_id not in admins: return
        user_states[user_id] = "waiting_rename_choice"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("اینستاگرام", callback_data="rename_insta"),
            types.InlineKeyboardButton("موزیک", callback_data="rename_music")
        )
        bot.answer_callback_query(call.id)
        bot.edit_message_text("✏️ کدام دکمه ویرایش شود؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data.startswith("rename_"):
        if user_id not in admins: return
        btn_key = data.replace("rename_", "")
        user_states[user_id] = f"set_name_{btn_key}"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "✍️ نام جدید دکمه را بفرستید:")

    elif data == "adm_move_btn":
        if user_id not in admins: return
        order = settings.get("btn_order", ["insta", "music"])
        user_states[user_id] = "waiting_reorder"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"🔀 ترتیب فعلی دکمه‌ها: `{' , '.join(order)}`\n\nترتیب جدید را با فاصله یا کاما بفرستید (کلیدها: `insta`, `music`):")

    elif data == "adm_back":
        if user_id not in admins: return
        bot.answer_callback_query(call.id)
        bot.edit_message_text("📌 **گزینه مورد نظر خود را انتخاب کنید:**", call.message.chat.id, call.message.message_id, reply_markup=get_main_menu_markup(user_id))

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check_sub(call):
    if check_membership(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ عضویت تایید شد!")
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        send_welcome(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ هنوز در کانال‌ها عضو نشده‌اید!", show_alert=True)

@bot.message_handler(content_types=['text'])
def handle_all_requests(message):
    user_id = message.from_user.id
    if is_banned(user_id): return
    save_user(message)
    settings = load_settings()
    channels = settings.get("channels", [])
    admins = settings.get("admins", INITIAL_ADMINS)

    if channels and not check_membership(user_id):
        bot.reply_to(message, "⚠️ لطفا ابتدا در کانال‌های ربات عضو شوید.")
        return

    current_state = user_states.get(user_id)
    text = message.text.strip() if message.text else ""

    # پنل مدیریت ادمین
    if user_id in admins:
        if current_state == "waiting_broadcast":
            for uid in load_users().keys():
                try: bot.send_message(int(uid), text)
                except: pass
            bot.reply_to(message, "✅ پیام همگانی ارسال شد.")
            user_states.pop(user_id, None)
            return

        elif current_state == "waiting_add_channel":
            ch = text if text.startswith("@") else "@" + text
            if ch not in settings["channels"]:
                settings["channels"].append(ch)
                save_settings(settings)
                bot.reply_to(message, f"✅ کانال {ch} افزوده شد.")
            else: bot.reply_to(message, "⚠️ کانال از قبل وجود دارد.")
            user_states.pop(user_id, None)
            return

        elif current_state == "waiting_remove_channel":
            ch = text if text.startswith("@") else "@" + text
            if ch in settings["channels"]:
                settings["channels"].remove(ch)
                save_settings(settings)
                bot.reply_to(message, f"🗑 کانال {ch} حذف شد.")
            else: bot.reply_to(message, "❌ کانال یافت نشد.")
            user_states.pop(user_id, None)
            return

        elif current_state == "waiting_ban_input":
            try:
                target = str(int(text))
                users = load_users()
                if target in users:
                    users[target]["banned"] = not users[target].get("banned", False)
                    save_json(USERS_FILE, users)
                    st = "مسدود 🚫" if users[target]["banned"] else "آزاد ✅"
                    bot.reply_to(message, f"کاربر {target} {st}")
                else: bot.reply_to(message, "❌ کاربر یافت نشد.")
            except: bot.reply_to(message, "❌ آیدی نامعتبر.")
            user_states.pop(user_id, None)
            return

        elif current_state == "waiting_user_msg_id":
            user_states[user_id] = f"send_msg_to_{text}"
            bot.reply_to(message, "💬 متنی که می‌خواهید به این کاربر ارسال کنید را بفرستید:")
            return

        elif current_state and current_state.startswith("send_msg_to_"):
            target_id = current_state.replace("send_msg_to_", "")
            try:
                bot.send_message(int(target_id), f"📩 پیام از طرف مدیریت:\n\n{text}")
                bot.reply_to(message, "✅ پیام ارسال شد.")
            except: bot.reply_to(message, "❌ ارسال پیام ناموفق بود.")
            user_states.pop(user_id, None)
            return

        elif current_state == "waiting_new_admin_id":
            try:
                new_adm = int(text)
                if new_adm not in settings["admins"]:
                    settings["admins"].append(new_adm)
                    save_settings(settings)
                    bot.reply_to(message, f"✅ ادمین جدید با آیدی {new_adm} افزوده شد.")
                else: bot.reply_to(message, "⚠️ کاربر از قبل ادمین است.")
            except: bot.reply_to(message, "❌ آیدی نامعتبر.")
            user_states.pop(user_id, None)
            return

        elif current_state and current_state.startswith("set_name_"):
            btn_key = current_state.replace("set_name_", "")
            settings["btn_names"][btn_key] = text
            save_settings(settings)
            bot.reply_to(message, f"✅ نام دکمه با موفقیت تغییر کرد.")
            user_states.pop(user_id, None)
            return

        elif current_state == "waiting_reorder":
            new_order = [x.strip() for x in text.replace(",", " ").split() if x.strip() in ["insta", "music"]]
            if len(new_order) == 2:
                settings["btn_order"] = new_order
                save_settings(settings)
                bot.reply_to(message, "✅ ترتیب دکمه‌ها با موفقیت بروز شد.")
            else: bot.reply_to(message, "❌ کلیدها نامعتبرند. دو کلید `insta`, `music` را وارد کنید.")
            user_states.pop(user_id, None)
            return

    if not (text.startswith("http://") or text.startswith("https://")):
        bot.reply_to(message, "❌ لطفاً ابتدا دکمه‌ای انتخاب کنید و سپس لینک بفرستید:", reply_markup=get_main_menu_markup(user_id))
        return

    status_msg = bot.reply_to(message, "⏳ در حال پردازش لینک...")
    try:
        if current_state == "waiting_insta" or "instagram.com" in text:
            ydl_opts = {'format': 'best', 'outtmpl': f'{DOWNLOAD_DIR}/t.me_zeucdl_bot_%(id)s.%(ext)s', 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=True)
                file_path = ydl.prepare_filename(info)
                if not os.path.exists(file_path): file_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp4'
                caption = info.get('description') or "بدون کپشن"

            if os.path.exists(file_path):
                with open(file_path, 'rb') as vid:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("🔗 اشتراک‌گذاری", url=text))
                    bot.send_video(message.chat.id, vid, caption=f"✅ دانلود انجام شد.\n\n{caption[:800]}\n\n🤖 t.me/zeucdl_bot", reply_markup=markup)
                bot.delete_message(message.chat.id, status_msg.message_id)
                bot.send_message(message.chat.id, "👇 گزینه بعدی:", reply_markup=get_main_menu_markup(user_id))
            user_states.pop(user_id, None)
            return

        elif current_state == "waiting_music" or "spotify.com" in text or "soundcloud.com" in text:
            target_url = text
            if "spotify.com" in text:
                try:
                    import urllib.request
                    req = urllib.request.Request(text, headers={'User-Agent': 'Mozilla/5.0'})
                    html = urllib.request.urlopen(req).read().decode('utf-8')
                    import re
                    m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                    if m: target_url = f"scsearch:{m.group(1)}"
                except: pass

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
                    bot.send_audio(message.chat.id, audio, caption="🎵 موزیک دانلود شده\n🤖 t.me/zeucdl_bot")
                bot.delete_message(message.chat.id, status_msg.message_id)
                bot.send_message(message.chat.id, "👇 گزینه بعدی:", reply_markup=get_main_menu_markup(user_id))
            user_states.pop(user_id, None)
            return

    except Exception as e:
        try: bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)
        except: pass
    finally: clear_downloads()

if __name__ == "__main__":
    web_thread = threading.Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    print("Bot & Web server are running...")
    try: bot.remove_webhook()
    except: pass
    bot.infinity_polling()
