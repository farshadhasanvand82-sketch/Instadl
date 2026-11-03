import os
import shutil
import threading
import json
import random
import base64
import urllib.request
import telebot
import yt_dlp
from flask import Flask
from telebot import types

BOT_TOKEN = "8948057491:AAEfaBcEn-PczAIAELBlliohnHKIpINPNGA"
INITIAL_ADMINS = [8886868325, 8250289921]

USERS_FILE = "users_data.json"
SETTINGS_FILE = "settings.json"
BOTS_FILE = "child_bots.json"

bot = telebot.TeleBot(BOT_TOKEN)
DOWNLOAD_DIR = "downloads"

user_states = {}
child_bot_instances = {}

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Professional Multi-Bot Builder & Downloader is running live!"

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
            "music": "🎵 دانلود اسپاتیفای/ساندکلود",
            "v2ray": "سرور v2rayرایگان",
            "builder": "ساخت ربات دانلودر"
        },
        "btn_order": ["insta", "music", "v2ray", "builder"]
    }
    data = load_json(SETTINGS_FILE, default_settings)
    if "channels" not in data: data["channels"] = []
    if "admins" not in data: data["admins"] = INITIAL_ADMINS
    if "btn_names" not in data: data["btn_names"] = default_settings["btn_names"]
    if "btn_order" not in data: data["btn_order"] = default_settings["btn_order"]
    return data

def save_settings(settings):
    save_json(SETTINGS_FILE, settings)

def load_child_bots():
    return load_json(BOTS_FILE, {})

def save_child_bots(bots):
    save_json(BOTS_FILE, bots)

def check_membership(user_id):
    settings = load_settings()
    admins = settings.get("admins", INITIAL_ADMINS)
    if user_id in admins:
        return True
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

def get_reply_keyboard(user_id):
    settings = load_settings()
    btn_names = settings.get("btn_names", {})
    btn_order = settings.get("btn_order", ["insta", "music", "v2ray", "builder"])
    admins = settings.get("admins", INITIAL_ADMINS)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard_buttons = []
    for key in btn_order:
        if key in btn_names:
            if key == "insta":
                keyboard_buttons.append(types.KeyboardButton(btn_names.get("insta", "📸 دانلود اینستاگرام")))
            elif key == "music":
                keyboard_buttons.append(types.KeyboardButton(btn_names.get("music", "🎵 دانلود اسپاتیفای/ساندکلود")))
            elif key == "v2ray":
                keyboard_buttons.append(types.KeyboardButton(btn_names.get("v2ray", "سرور v2rayرایگان")))
            elif key == "builder":
                keyboard_buttons.append(types.KeyboardButton(btn_names.get("builder", "ساخت ربات دانلودر")))
            
    if keyboard_buttons:
        markup.add(*keyboard_buttons)
    if user_id in admins and not user_states.get(user_id) == "guest_mode":
        markup.add(types.KeyboardButton("⚙️ پنل مدیریت پیشرفته"))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if is_banned(user_id): return
    save_user(message)
    settings = load_settings()
    channels = settings.get("channels", [])
    admins = settings.get("admins", INITIAL_ADMINS)
    
    is_guest = (user_states.get(user_id) == "guest_mode")

    if channels and user_id not in admins and not check_membership(user_id):
        markup = types.InlineKeyboardMarkup()
        for ch in channels:
            markup.add(types.InlineKeyboardButton(f"📢 عضويت در {ch}", url=f"https://t.me/{ch.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("🔄 عضو شدم، بررسی مجدد", callback_data="check_sub"))
        bot.reply_to(message, "⚠️ برای استفاده از ربات ابتدا باید در کانال‌های زیر عضو شوید:", reply_markup=markup)
        return

    mode_text = " (حالت تست مهمان 🕵️‍♂️)" if is_guest else ""
    bot.reply_to(
        message,
        f"سلام! 🤖{mode_text}\nبه ربات پیشرفته دانلود رسانه خوش آمدید.\n\n📌 **گزینه مورد نظر خود را از کیبورد پایین انتخاب کنید:**",
        reply_markup=get_reply_keyboard(user_id)
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_router(call):
    user_id = call.from_user.id
    data = call.data
    settings = load_settings()
    admins = settings.get("admins", INITIAL_ADMINS)

    if user_id not in admins and data != "check_sub":
        bot.answer_callback_query(call.id, "❌ دسترسی غیرمجاز!", show_alert=True)
        return

    if data == "check_sub":
        if check_membership(user_id):
            bot.answer_callback_query(call.id, "✅ عضویت تایید شد!")
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ هنوز در کانال‌ها عضو نشده‌اید!", show_alert=True)
        return

    if data == "adm_stats":
        users = load_users()
        child_bots = load_child_bots()
        total = len(users)
        banned = sum(1 for u in users.values() if u.get("banned"))
        ch_list = ", ".join(settings.get("channels", [])) or "ندارد"
        total_bots = len(child_bots)
        text = f"📊 **آمار ربات:**\n\n👥 کل کاربران: {total}\n🚫 مسدود شده‌ها: {banned}\n🤖 ربات‌های ساخته شده: {total_bots}\n📢 کانال‌های قفل: {ch_list}"
        bot.answer_callback_query(call.id)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

    elif data == "adm_broadcast":
        user_states[user_id] = "waiting_broadcast"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "💬 متن پیام همگانی را بفرستید:", reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("📤 پیام همگانی ربات اصلی", callback_data="bc_main")
        ))

    elif data == "bc_main":
        user_states[user_id] = "waiting_main_broadcast"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "💬 متن پیام همگانی برای کاربران ربات اصلی را بفرستید:")

    elif data == "adm_channels_mgmt":
        channels = settings.get("channels", [])
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("➕ افزودن کانال جدید", callback_data="adm_add_ch"))
        for ch in channels:
            markup.add(types.InlineKeyboardButton(f"❌ حذف کانال: {ch}", callback_data=f"del_ch_{ch}"))
        markup.add(types.InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="adm_back"))
        bot.answer_callback_query(call.id)
        bot.edit_message_text("📢 **مدیریت کانال‌های قفل (ربات اصلی):**", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data.startswith("del_ch_"):
        ch_to_del = data.replace("del_ch_", "")
        if ch_to_del in settings["channels"]:
            settings["channels"].remove(ch_to_del)
            save_settings(settings)
            bot.answer_callback_query(call.id, f"✅ کانال {ch_to_del} حذف شد!", show_alert=True)
            channels = settings.get("channels", [])
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("➕ افزودن کانال جدید", callback_data="adm_add_ch"))
            for ch in channels:
                markup.add(types.InlineKeyboardButton(f"❌ حذف کانال: {ch}", callback_data=f"del_ch_{ch}"))
            markup.add(types.InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="adm_back"))
            bot.edit_message_text("📢 **مدیریت کانال‌های قفل (ربات اصلی):**", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "adm_add_ch":
        user_states[user_id] = "waiting_add_channel"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📢 آیدی کانال را بفرستید (مثل `@channel`):")

    elif data == "adm_users_mgmt":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🚫 مسدود/آزاد کردن کاربر", callback_data="adm_ban_user"),
            types.InlineKeyboardButton("✉️ ارسال پیام به کاربر", callback_data="adm_msg_user"),
            types.InlineKeyboardButton("➕ افزودن ادمین جدید", callback_data="adm_add_admin"),
            types.InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="adm_back")
        )
        bot.answer_callback_query(call.id)
        bot.edit_message_text("👥 **مدیریت کاربران و ادمین‌ها:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "adm_ban_user":
        user_states[user_id] = "waiting_ban_input"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🚫 آیدی عددی کاربر را بفرستید:")

    elif data == "adm_msg_user":
        user_states[user_id] = "waiting_user_msg_id"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "✉️ ابتدا آیدی عددی کاربر را بفرستید:")

    elif data == "adm_add_admin":
        user_states[user_id] = "waiting_new_admin_id"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "➕ آیدی عددی کاربر جدید را بفرستید:")

    elif data == "adm_child_bots_mgmt":
        child_bots = load_child_bots()
        markup = types.InlineKeyboardMarkup(row_width=1)
        if not child_bots:
            markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm_back"))
            bot.answer_callback_query(call.id)
            bot.edit_message_text("🤖 هیچ رباتی تا کنون ساخته نشده است.", call.message.chat.id, call.message.message_id, reply_markup=markup)
            return
        
        for b_token, b_info in child_bots.items():
            ch_status = b_info.get('channel') or 'ندارد'
            markup.add(types.InlineKeyboardButton(f"🤖 @{b_info['username']} | قفل: {ch_status}", callback_data=f"manage_child_{b_token}"))
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm_back"))
        bot.answer_callback_query(call.id)
        bot.edit_message_text(f"🤖 **مدیریت ربات‌های ساخته شده:**\nروی هر ربات کلیک کنید تا قفل کانال تنظیم کنید یا آن را حذف نمایید:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data.startswith("manage_child_"):
        b_token = data.replace("manage_child_", "")
        child_bots = load_child_bots()
        if b_token in child_bots:
            b_info = child_bots[b_token]
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("📢 تنظیم/تغییر کانال قفل این ربات", callback_data=f"child_set_ch_{b_token}"),
                types.InlineKeyboardButton("❌ حذف و خاموش کردن این ربات", callback_data=f"del_bot_{b_token}"),
                types.InlineKeyboardButton("🔙 بازگشت به لیست ربات‌ها", callback_data="adm_child_bots_mgmt")
            )
            bot.answer_callback_query(call.id)
            bot.edit_message_text(f"🤖 **مدیریت ربات:** `@{b_info['username']}`\n📌 کانال قفل فعلی: `{b_info.get('channel') or 'تنظیم نشده'}`", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data.startswith("child_set_ch_"):
        b_token = data.replace("child_set_ch_", "")
        user_states[user_id] = f"waiting_child_ch_{b_token}"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📢 آیدی کانال قفل را برای این ربات بفرستید (برای حذف کلمه `off` را بفرستید):")

    elif data.startswith("del_bot_"):
        b_token = data.replace("del_bot_", "")
        child_bots = load_child_bots()
        if b_token in child_bots:
            del child_bots[b_token]
            save_child_bots(child_bots)
            bot.answer_callback_query(call.id, "✅ ربات با موفقیت حذف شد!", show_alert=True)
            markup = types.InlineKeyboardMarkup(row_width=1)
            for tk, inf in child_bots.items():
                markup.add(types.InlineKeyboardButton(f"🤖 @{inf['username']}", callback_data=f"manage_child_{tk}"))
            markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm_back"))
            bot.edit_message_text(f"🤖 **مدیریت ربات‌های ساخته شده:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "adm_buttons_mgmt":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✏️ تغییر نام دکمه‌ها", callback_data="adm_rename_btn"),
            types.InlineKeyboardButton("🗑 حذف/پنهان کردن دکمه‌ها", callback_data="adm_delete_btn_menu"),
            types.InlineKeyboardButton("🔀 جابجایی ترتیب دکمه‌ها", callback_data="adm_move_btn"),
            types.InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="adm_back")
        )
        bot.answer_callback_query(call.id)
        bot.edit_message_text("🎛 **مدیریت دکمه‌های منو:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "adm_rename_btn":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("تغییر نام اینستاگرام", callback_data="rename_insta"),
            types.InlineKeyboardButton("تغییر نام موزیک", callback_data="rename_music"),
            types.InlineKeyboardButton("تغییر نام سرور v2ray", callback_data="rename_v2ray"),
            types.InlineKeyboardButton("تغییر نام ساخت ربات", callback_data="rename_builder"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm_buttons_mgmt")
        )
        bot.answer_callback_query(call.id)
        bot.edit_message_text("🎛 کدام دکمه ویرایش شود؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "adm_delete_btn_menu":
        order = settings.get("btn_order", ["insta", "music", "v2ray", "builder"])
        btn_names = settings.get("btn_names", {})
        markup = types.InlineKeyboardMarkup(row_width=1)
        for key in order:
            b_title = btn_names.get(key, key)
            markup.add(types.InlineKeyboardButton(f"❌ حذف دکمه: {b_title}", callback_data=f"remove_btn_{key}"))
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm_buttons_mgmt"))
        bot.answer_callback_query(call.id)
        bot.edit_message_text("🗑 برای حذف هر دکمه از منوی اصلی، روی آن کلیک کنید:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data.startswith("remove_btn_"):
        btn_to_remove = data.replace("remove_btn_", "")
        if btn_to_remove in settings["btn_order"]:
            settings["btn_order"].remove(btn_to_remove)
            save_settings(settings)
            bot.answer_callback_query(call.id, "✅ دکمه با موفقیت حذف شد!", show_alert=True)
            order = settings.get("btn_order", [])
            btn_names = settings.get("btn_names", {})
            markup = types.InlineKeyboardMarkup(row_width=1)
            for key in order:
                b_title = btn_names.get(key, key)
                markup.add(types.InlineKeyboardButton(f"❌ حذف دکمه: {b_title}", callback_data=f"remove_btn_{key}"))
            markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm_buttons_mgmt"))
            bot.edit_message_text("🗑 برای حذف هر دکمه از منوی اصلی، روی آن کلیک کنید:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data.startswith("rename_"):
        btn_key = data.replace("rename_", "")
        user_states[user_id] = f"set_name_{btn_key}"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "✍️ نام جدید دکمه را بفرستید:")

    elif data == "adm_move_btn":
        order = settings.get("btn_order", ["insta", "music", "v2ray", "builder"])
        user_states[user_id] = "waiting_reorder"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"🔀 ترتیب فعلی دکمه‌ها: `{' , '.join(order)}`\n\nکلیدهای موجود: `insta`, `music`, `v2ray`, `builder`\nترتیب جدید را با فاصله یا کاما بفرستید:")

    elif data == "adm_back":
        if user_id not in admins: return
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📊 آمار کاربران", callback_data="adm_stats"),
            types.InlineKeyboardButton("📢 ارسال همگانی", callback_data="adm_broadcast"),
            types.InlineKeyboardButton("📢 مدیریت کانال‌های قفل", callback_data="adm_channels_mgmt"),
            types.InlineKeyboardButton("👥 مدیریت کاربران و ادمین‌ها", callback_data="adm_users_mgmt"),
            types.InlineKeyboardButton("🤖 مدیریت ربات‌های ساخته شده", callback_data="adm_child_bots_mgmt"),
            types.InlineKeyboardButton("🎛 مدیریت دکمه‌ها", callback_data="adm_buttons_mgmt")
        )
        bot.edit_message_text("🛠 **پنل مدیریت پیشرفته ربات:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.message_handler(content_types=['text'])
def handle_all_requests(message):
    user_id = message.from_user.id
    if is_banned(user_id): return
    save_user(message)
    settings = load_settings()
    channels = settings.get("channels", [])
    admins = settings.get("admins", INITIAL_ADMINS)

    is_guest = (user_states.get(user_id) == "guest_mode")

    if channels and user_id not in admins and not check_membership(user_id):
        bot.reply_to(message, "⚠️ لطفا ابتدا در کانال‌های ربات عضو شوید.")
        return
    if channels and user_id in admins and is_guest and not check_membership(user_id):
        bot.reply_to(message, "⚠️ [حالت تست مهمان] شما به عنوان کاربر عادی باید در کانال عضو باشید. برای خروج /start را بزنید.")
        return

    text = message.text.strip() if message.text else ""
    current_state = user_states.get(user_id)
    btn_names = settings.get("btn_names", {})

    if user_id in admins and not is_guest:
        if text == "⚙️ پنل مدیریت پیشرفته":
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("📊 آمار کاربران", callback_data="adm_stats"),
                types.InlineKeyboardButton("📢 ارسال همگانی", callback_data="adm_broadcast"),
                types.InlineKeyboardButton("📢 مدیریت کانال‌های قفل", callback_data="adm_channels_mgmt"),
                types.InlineKeyboardButton("👥 مدیریت کاربران و ادمین‌ها", callback_data="adm_users_mgmt"),
                types.InlineKeyboardButton("🤖 مدیریت ربات‌های ساخته شده", callback_data="adm_child_bots_mgmt"),
                types.InlineKeyboardButton("🎛 مدیریت دکمه‌ها", callback_data="adm_buttons_mgmt"),
                types.InlineKeyboardButton("🕵️‍♂️ ورود به حالت تست مهمان", callback_data="dummy_guest")
            )
            bot.reply_to(message, "🛠 **پنل مدیریت پیشرفته ربات:**", reply_markup=markup)
            return

        if text == "🕵️‍♂️ ورود به حالت تست مهمان" or text == "/guest":
            user_states[user_id] = "guest_mode"
            bot.reply_to(message, "🕵️‍♂️ **شما وارد حالت تست مهمان شدید!**\nبرای خروج و بازگشت به پنل مدیریت، `/start` را بفرستید.", reply_markup=get_reply_keyboard(user_id))
            return

        if current_state == "waiting_main_broadcast":
            for uid in load_users().keys():
                try: bot.send_message(int(uid), text)
                except: pass
            bot.reply_to(message, "✅ پیام همگانی به کاربران ربات اصلی ارسال شد.", reply_markup=get_reply_keyboard(user_id))
            user_states.pop(user_id, None)
            return

        elif current_state and current_state.startswith("waiting_child_ch_"):
            b_token = current_state.replace("waiting_child_ch_", "")
            child_bots = load_child_bots()
            if b_token in child_bots:
                if text.lower() == "off":
                    child_bots[b_token]["channel"] = ""
                    bot.reply_to(message, "✅ قفل کانال این ربات غیرفعال شد.", reply_markup=get_reply_keyboard(user_id))
                else:
                    ch = text if text.startswith("@") else "@" + text
                    child_bots[b_token]["channel"] = ch
                    bot.reply_to(message, f"✅ کانال قفل این ربات روی `{ch}` تنظیم شد.", reply_markup=get_reply_keyboard(user_id))
                save_child_bots(child_bots)
            user_states.pop(user_id, None)
            return

        elif current_state == "waiting_add_channel":
            ch = text if text.startswith("@") else "@" + text
            if ch not in settings["channels"]:
                settings["channels"].append(ch)
                save_settings(settings)
                bot.reply_to(message, f"✅ کانال {ch} افزوده شد.", reply_markup=get_reply_keyboard(user_id))
            else: bot.reply_to(message, "⚠️ کانال از قبل وجود دارد.", reply_markup=get_reply_keyboard(user_id))
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
                    bot.reply_to(message, f"کاربر {target} {st}", reply_markup=get_reply_keyboard(user_id))
                else: bot.reply_to(message, "❌ کاربر یافت نشد.", reply_markup=get_reply_keyboard(user_id))
            except: bot.reply_to(message, "❌ آیدی نامعتبر.", reply_markup=get_reply_keyboard(user_id))
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
                bot.reply_to(message, "✅ پیام ارسال شد.", reply_markup=get_reply_keyboard(user_id))
            except: bot.reply_to(message, "❌ ارسال پیام ناموفق بود.", reply_markup=get_reply_keyboard(user_id))
            user_states.pop(user_id, None)
            return

        elif current_state == "waiting_new_admin_id":
            try:
                new_adm = int(text)
                if new_adm not in settings["admins"]:
                    settings["admins"].append(new_adm)
                    save_settings(settings)
                    bot.reply_to(message, f"✅ ادمین جدید با آیدی {new_adm} افزوده شد.", reply_markup=get_reply_keyboard(user_id))
                else: bot.reply_to(message, "⚠️ کاربر از قبل ادمین است.", reply_markup=get_reply_keyboard(user_id))
            except: bot.reply_to(message, "❌ آیدی نامعتبر.", reply_markup=get_reply_keyboard(user_id))
            user_states.pop(user_id, None)
            return

        elif current_state and current_state.startswith("set_name_"):
            btn_key = current_state.replace("set_name_", "")
            settings["btn_names"][btn_key] = text
            save_settings(settings)
            bot.reply_to(message, f"✅ نام دکمه تغییر کرد!", reply_markup=get_reply_keyboard(user_id))
            user_states.pop(user_id, None)
            return

        elif current_state == "waiting_reorder":
            new_order = [x.strip() for x in text.replace(",", " ").split() if x.strip() in ["insta", "music", "v2ray", "builder"]]
            if len(new_order) > 0:
                settings["btn_order"] = new_order
                save_settings(settings)
                bot.reply_to(message, "✅ ترتیب دکمه‌ها بروز شد.", reply_markup=get_reply_keyboard(user_id))
            else: bot.reply_to(message, "❌ کلیدها نامعتبرند.", reply_markup=get_reply_keyboard(user_id))
            user_states.pop(user_id, None)
            return

    if text == "/start" and user_id in admins:
        user_states.pop(user_id, None)

    if text == "👨‍💻 سازنده" or text == "سازنده":
        bot.reply_to(message, "🤖 **این ربات با سیستم پیشرفته ساخت ربات ساخته شده است.**\n\n📌 سازنده و پشتیبان اصلی:\n@izeucs", reply_markup=get_reply_keyboard(user_id))
        return

    if text == btn_names.get("builder", "ساخت ربات دانلودر"):
        user_states[user_id] = "waiting_bot_token"
        bot.reply_to(message, "🤖 **ساخت ربات دانلودر اختصاصی:**\n\nلطفاً توکن ربات خود را از `@BotFather` بفرستید:", reply_markup=get_reply_keyboard(user_id))
        return

    if current_state == "waiting_bot_token":
        new_token = text.strip()
        try:
            test_bot = telebot.TeleBot(new_token)
            bot_info = test_bot.get_me()
            bot_username = bot_info.username

            child_bots = load_child_bots()
            if new_token in child_bots:
                bot.reply_to(message, f"⚠️ این ربات (`@{bot_username}`) قبلاً ثبت شده است.", reply_markup=get_reply_keyboard(user_id))
            else:
                child_bots[new_token] = {"owner": user_id, "username": bot_username, "channel": ""}
                save_child_bots(child_bots)
                start_child_bot(new_token)
                bot.reply_to(message, f"✅ **تبریک! ربات شما ساخته شد.**\n\n🤖 آیدی ربات: @{bot_username}", reply_markup=get_reply_keyboard(user_id))
        except Exception as e:
            bot.reply_to(message, f"❌ توکن نامعتبر است:\n{str(e)}", reply_markup=get_reply_keyboard(user_id))
        user_states.pop(user_id, None)
        return

    if text == btn_names.get("v2ray", "سرور v2rayرایگان"):
        status_msg = bot.reply_to(message, "⏳ در حال دریافت سرور رندوم V2Ray...")
        try:
            target_sub_url = "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/mix"
            req = urllib.request.Request(target_sub_url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req)
            content = response.read().decode('utf-8')
            try:
                decoded_bytes = base64.b64decode(content.strip())
                content_decoded = decoded_bytes.decode('utf-8')
                lines = [line.strip() for line in content_decoded.splitlines() if line.strip()]
            except:
                lines = [line.strip() for line in content.splitlines() if line.strip()]
            if lines:
                selected_config = random.choice(lines)
                bot.delete_message(message.chat.id, status_msg.message_id)
                bot.reply_to(message, f"🌐 **سرور رایگان V2Ray (رندوم):**\n\n`{selected_config}`", parse_mode="Markdown", reply_markup=get_reply_keyboard(user_id))
            else:
                bot.edit_message_text("❌ سروری یافت نشد.", message.chat.id, status_msg.message_id)
        except Exception as e:
            try: bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)
            except: pass
        return

    if text == btn_names.get("insta", "📸 دانلود اینستاگرام"):
        user_states[user_id] = "waiting_insta"
        bot.reply_to(message, "📸 **بخش اینستاگرام فعال شد.**\n\nلینک پست یا ریلز را بفرستید:", reply_markup=get_reply_keyboard(user_id))
        return

    elif text == btn_names.get("music", "🎵 دانلود اسپاتیفای/ساندکلود"):
        user_states[user_id] = "waiting_music"
        bot.reply_to(message, "🎵 **بخش موزیک فعال شد.**\n\nلینک آهنگ را بفرستید:", reply_markup=get_reply_keyboard(user_id))
        return

    if not (text.startswith("http://") or text.startswith("https://")):
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
            user_states.pop(user_id, None)
            return

        elif current_state == "waiting_music" or "spotify.com" in text or "soundcloud.com" in text:
            target_url = text
            if "spotify.com" in text:
                try:
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
            user_states.pop(user_id, None)
            return

    except Exception as e:
        try: bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)
        except: pass
    finally: clear_downloads()

# سیستم اجرای ربات‌های فرزند (Builder Bot Worker)
def run_child_bot(token):
    try:
        c_bot = telebot.TeleBot(token)
        
        def check_child_membership(uid, tok):
            cbots = load_child_bots()
            ch = cbots.get(tok, {}).get("channel")
            if not ch: return True
            try:
                member = c_bot.get_chat_member(ch, uid)
                if member.status in ['member', 'administrator', 'creator']: return True
            except: pass
            return False

        @c_bot.message_handler(commands=['start'])
        def child_start(msg):
            uid = msg.from_user.id
            cbots = load_child_bots()
            ch = cbots.get(token, {}).get("channel")
            if ch and not check_child_membership(uid, token):
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(f"📢 عضویت در {ch}", url=f"https://t.me/{ch.replace('@','')}"))
                markup.add(types.InlineKeyboardButton("🔄 بررسی عضویت", callback_data="child_check"))
                c_bot.reply_to(msg, f"⚠️ برای استفاده از این ربات ابتدا باید در کانال زیر عضو شوید:\n{ch}", reply_markup=markup)
                return

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(types.KeyboardButton("📸 دانلود اینستاگرام"), types.KeyboardButton("🎵 دانلود موزیک"), types.KeyboardButton("👨‍💻 سازنده"))
            c_bot.reply_to(msg, "سلام! 🤖\nبه ربات اختصاصی دانلود رسانه خوش آمدید.\n\nگزینه مورد نظر را انتخاب کنید:", reply_markup=markup)

        @c_bot.callback_query_handler(func=lambda call: call.data == "child_check")
        def child_check_sub(call):
            if check_child_membership(call.from_user.id, token):
                c_bot.answer_callback_query(call.id, "✅ تایید شد!")
                try: c_bot.delete_message(call.message.chat.id, call.message.message_id)
                except: pass
                child_start(call.message)
            else:
                c_bot.answer_callback_query(call.id, "❌ هنوز عضو نشده‌اید!", show_alert=True)

        @c_bot.message_handler(content_types=['text'])
        def child_handle(msg):
            uid = msg.from_user.id
            cbots = load_child_bots()
            ch = cbots.get(token, {}).get("channel")
            if ch and not check_child_membership(uid, token):
                c_bot.reply_to(msg, "⚠️ لطفا ابتدا در کانال ربات عضو شوید.")
                return

            txt = msg.text.strip()
            if txt == "👨‍💻 سازنده":
                c_bot.reply_to(msg, "🤖 **این ربات با سیستم پیشرفته ما ساخته شده است.**\n\n📌 ربات سازنده اصلی:\n@izeucs")
            elif txt == "📸 دانلود اینستاگرام":
                c_bot.reply_to(msg, "لینک پست اینستاگرام خود را بفرستید:")
            elif txt == "🎵 دانلود موزیک":
                c_bot.reply_to(msg, "لینک آهنگ را بفرستید:")
            elif txt.startswith("http://") or txt.startswith("https://"):
                status = c_bot.reply_to(msg, "⏳ در حال پردازش و دانلود...")
                try:
                    ydl_opts = {'format': 'best', 'outtmpl': f'{DOWNLOAD_DIR}/child_%(id)s.%(ext)s', 'quiet': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(txt, download=True)
                        f_path = ydl.prepare_filename(info)
                        if not os.path.exists(f_path): f_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp4'
                    if os.path.exists(f_path):
                        with open(f_path, 'rb') as f_vid:
                            c_bot.send_video(msg.chat.id, f_vid, caption="✅ دانلود انجام شد.")
                        c_bot.delete_message(msg.chat.id, status.message_id)
                except Exception as e:
                    c_bot.edit_message_text(f"❌ خطا در دانلود: {str(e)}", msg.chat.id, status.message_id)
            else:
                c_bot.reply_to(msg, "لطفاً یک لینک معتبر ارسال کنید.")

        c_bot.remove_webhook()
        child_bot_instances[token] = c_bot
        c_bot.infinity_polling(none_stop=True)
    except Exception as e:
        print(f"Child bot error for token {token[:8]}...: {e}")

def start_child_bot(token):
    t = threading.Thread(target=run_child_bot, args=(token,))
    t.daemon = True
    t.start()

def init_saved_child_bots():
    child_bots = load_child_bots()
    for token in child_bots.keys():
        start_child_bot(token)

if __name__ == "__main__":
    init_saved_child_bots()
    web_thread = threading.Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    print("Bot & Web server are running...")
    try: bot.remove_webhook()
    except: pass
    bot.infinity_polling()
