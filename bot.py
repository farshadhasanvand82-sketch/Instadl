import os
import shutil
import threading
import time
import json
import random
import base64
import re
import telebot
import yt_dlp
from flask import Flask
from telebot import types

BOT_TOKEN = "8948057491:AAGcZ6DH_gPhSOPqcAPz7XU-PM391_mJ0Ns"
INITIAL_ADMINS = [8886868325, 8250289921]

ARCHIVE_CHANNEL = "@sheGOgpUlFVmMTRk"

DATA_DIR = "/data" if os.path.exists("/data") else "."
USERS_FILE = os.path.join(DATA_DIR, "users_data.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
BOTS_FILE = os.path.join(DATA_DIR, "child_bots.json")
PRO_STATE_FILE = os.path.join(DATA_DIR, "pro_state.json")
POSTS_CACHE_FILE = os.path.join(DATA_DIR, "posts_cache.json")
USER_LAST_URL_FILE = os.path.join(DATA_DIR, "user_last_url.json")
MUSIC_CHOICES_FILE = os.path.join(DATA_DIR, "music_choices.json")

bot = telebot.TeleBot(BOT_TOKEN)
DOWNLOAD_DIR = "downloads"

user_states = {}
child_bot_instances = {}
child_bot_threads = {}
rename_temp_data = {} 

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Professional Multi-Bot Builder & Downloader is running live!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def self_ping_worker():
    import urllib.request
    time.sleep(10)
    while True:
        try:
            app_url = os.environ.get("RENDER_EXTERNAL_URL")
            if app_url:
                urllib.request.urlopen(app_url, timeout=10)
        except Exception as e:
            print(f"Self-ping error: {e}")
        time.sleep(240)

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
        "banned": False,
        "subscription_expire": 0 
    }
    if user_id not in users:
        users[user_id] = user_data
        save_json(USERS_FILE, users)

def is_banned(user_id):
    users = load_users()
    return users.get(str(user_id), {}).get("banned", False)

def has_active_subscription(user_id):
    admins = load_settings().get("admins", INITIAL_ADMINS)
    if user_id in admins:
        return True
    users = load_users()
    user_data = users.get(str(user_id), {})
    expire_time = user_data.get("subscription_expire", 0)
    return expire_time > time.time()

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
        "btn_order": ["insta", "music", "v2ray", "builder"],
        "pro_sources": [],
        "pro_dest": "",
        "pro_name": "VIP Server"
    }
    data = load_json(SETTINGS_FILE, default_settings)
    if "channels" not in data: data["channels"] = []
    if "admins" not in data: data["admins"] = INITIAL_ADMINS
    if "btn_names" not in data: data["btn_names"] = default_settings["btn_names"]
    if "btn_order" not in data: data["btn_order"] = default_settings["btn_order"]
    if "pro_sources" not in data: data["pro_sources"] = []
    if "pro_dest" not in data: data["pro_dest"] = ""
    if "pro_name" not in data: data["pro_name"] = "VIP Server"
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

def fetch_channel_web_updates():
    import urllib.request
    import urllib.parse
    import html as html_parser

    processed_posts = load_json(PRO_STATE_FILE, {})
    
    while True:
        try:
            settings = load_settings()
            sources = settings.get("pro_sources", [])
            dest_ch = settings.get("pro_dest")
            new_name = settings.get("pro_name", "VIP Server")

            if sources and dest_ch:
                for src in sources:
                    clean_src = src.replace("@", "").strip()
                    if not clean_src: continue
                    
                    url = f"https://t.me/s/{clean_src}"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    try:
                        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
                    except Exception as e:
                        continue
                    
                    posts = re.findall(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', html, re.DOTALL)
                    for post_html in posts:
                        clean_text = re.sub(r'<[^>]+>', '\n', post_html)
                        clean_text = html_parser.unescape(clean_text)
                        
                        post_id = str(hash(clean_text))
                        
                        if clean_src not in processed_posts:
                            processed_posts[clean_src] = []
                            
                        if post_id not in processed_posts[clean_src]:
                            configs = re.findall(r'(?:vmess|vless|trojan|ss|ssr)://[^\s<>]+', clean_text)
                            if configs:
                                for idx, cfg in enumerate(configs):
                                    cfg = cfg.rstrip('`"\'.,;:)]}>')
                                    if "#" in cfg:
                                        base_cfg = cfg.rsplit("#", 1)[0]
                                        encoded_name = urllib.parse.quote(f"{new_name} {idx+1}")
                                        final_cfg = f"{base_cfg}#{encoded_name}"
                                    else:
                                        encoded_name = urllib.parse.quote(f"{new_name} {idx+1}")
                                        final_cfg = f"{cfg}#{encoded_name}"
                                    
                                    msg_to_send = f"`{final_cfg}`\n\n{dest_ch}"
                                    try:
                                        bot.send_message(dest_ch, msg_to_send, parse_mode="Markdown")
                                    except Exception as err:
                                        print(f"Error sending to dest: {err}")
                            
                            processed_posts[clean_src].append(post_id)
                            if len(processed_posts[clean_src]) > 100:
                                processed_posts[clean_src].pop(0)
                                
                    save_json(PRO_STATE_FILE, processed_posts)
        except Exception as e:
            print(f"Background fetch error: {e}")
        
        time.sleep(60)

def generate_users_page(page=0, search_query=""):
    users = load_users()
    user_items = list(users.items())
    
    if search_query:
        sq = search_query.lower()
        user_items = [
            (uid, udata) for uid, udata in user_items 
            if sq in uid.lower() or sq in udata.get("username", "").lower() or sq in udata.get("first_name", "").lower()
        ]

    per_page = 6
    total_users = len(user_items)
    max_pages = (total_users + per_page - 1) // per_page
    if page >= max_pages and max_pages > 0:
        page = max_pages - 1
    if page < 0:
        page = 0

    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_slice = user_items[start_idx:end_idx]

    markup = types.InlineKeyboardMarkup(row_width=1)
    now = time.time()

    for uid, udata in current_slice:
        name = udata.get("first_name", "بدون نام")
        uname = udata.get("username", "ندارد")
        expire = udata.get("subscription_expire", 0)
        
        has_sub = expire > now
        if has_sub:
            days_left = int((expire - now) / 86400)
            sub_status = f"🟢 اشتراک فعال ({days_left} روز)"
        else:
            sub_status = "🔴 بدون اشتراک"

        btn_text = f"{name} (@{uname}) | {sub_status}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"adm_usr_opt_{uid}"))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ صفحه قبل", callback_data=f"adm_users_page_{page-1}_{search_query}"))
    if page < max_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("صفحه بعد ➡️", callback_data=f"adm_users_page_{page+1}_{search_query}"))
    
    if nav_buttons:
        markup.row(*nav_buttons)

    markup.add(
        types.InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="adm_users_search"),
        types.InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="adm_back")
    )
    
    text = f"👥 **لیست کاربران ربات** (صفحه {page+1} از {max_pages or 1})\n📌 کل کاربران یافت شده: {total_users}\n\nبرای مدیریت اشتراک روی نام هر کاربر کلیک کنید:"
    return text, markup

@bot.callback_query_handler(func=lambda call: True)
def callback_router(call):
    user_id = call.from_user.id
    data = call.data
    settings = load_settings()
    admins = settings.get("admins", INITIAL_ADMINS)

    if data == "check_sub":
        if check_membership(user_id):
            bot.answer_callback_query(call.id, "✅ عضویت تایید شد!")
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ هنوز در کانال‌ها عضو نشده‌اید!", show_alert=True)
        return

    # شناسایی موزیک بر اساس آخرین لینک ارسالی همان کاربر با نمایش درصد پیشرفت
    if data.startswith("find_music_"):
        user_last_urls = load_json(USER_LAST_URL_FILE, {})
        target_url = user_last_urls.get(str(user_id))

        if not target_url:
            bot.answer_callback_query(call.id, "❌ هیچ لینک فعالی از شما ثبت نشده است. لطفاً ابتدا لینک پست را بفرستید.", show_alert=True)
            return

        bot.answer_callback_query(call.id, "🎵 شروع استخراج موزیک از آخرین لینک...")
        status_msg = bot.send_message(call.message.chat.id, "🎧 استخراج متادیتا و اتصال به موتور جستجو: 20%")

        def process_user_last_url_search(chat_id, url, msg_to_del):
            try:
                try: bot.edit_message_text("🎧 تحلیل اطلاعات پست: 50%", chat_id, msg_to_del.message_id)
                except: pass

                meta_opts = {'format': 'best', 'quiet': True}
                search_query = "ahang jadid persian remix"
                
                with yt_dlp.YoutubeDL(meta_opts) as m_ydl:
                    m_info = m_ydl.extract_info(url, download=False)
                    t_title = m_info.get('title')
                    t_desc = m_info.get('description') or ""
                    
                    if t_title and len(t_title.strip()) > 3:
                        search_query = t_title[:50]
                    else:
                        lines = [l.strip() for l in t_desc.splitlines() if len(l.strip()) > 4]
                        if lines:
                            search_query = lines[0][:50]

                try: bot.edit_message_text("🔍 جستجوی دقیق موزیک کامل: 80%", chat_id, msg_to_del.message_id)
                except: pass

                entries = []
                music_search_opts = {'format': 'bestaudio', 'quiet': True, 'noplaylist': True}
                with yt_dlp.YoutubeDL(music_search_opts) as m_ydl:
                    res = m_ydl.extract_info(f"scsearch10:{search_query}", download=False)
                    if res and 'entries' in res:
                        entries.extend(res['entries'])

                if not entries:
                    res2 = m_ydl.extract_info(f"scsearch10:ahang jadid persian remix", download=False)
                    if res2 and 'entries' in res2:
                        entries.extend(res2['entries'])

                if not entries:
                    bot.edit_message_text("❌ آهنگی برای این لینک یافت نشد (100%).", chat_id, msg_to_del.message_id)
                    return

                try: bot.edit_message_text("✅ جستجوی صوتی کامل شد: 100%", chat_id, msg_to_del.message_id)
                except: pass

                music_choices = load_json(MUSIC_CHOICES_FILE, {})
                markup = types.InlineKeyboardMarkup(row_width=1)
                
                unique_entries = {}
                for entry in entries:
                    if entry and 'webpage_url' in entry:
                        unique_entries[entry['webpage_url']] = entry

                for idx, (m_url, entry) in enumerate(list(unique_entries.items())[:6]):
                    m_title = entry.get('title', 'آهنگ ناشناخته')
                    choice_id = f"mc_{random.randint(10000, 99999)}"
                    music_choices[choice_id] = m_url
                    markup.add(types.InlineKeyboardButton(f"🎵 {m_title[:50]}", callback_data=choice_id))

                save_json(MUSIC_CHOICES_FILE, music_choices)
                bot.send_message(chat_id, "📌 لطفاً آهنگ کامل و واقعی مورد نظر خود را از لیست زیر انتخاب کنید (100%):", reply_markup=markup)

            except Exception as e:
                try: bot.edit_message_text(f"❌ خطا در پردازش: {str(e)}", chat_id, msg_to_del.message_id)
                except: pass
            finally:
                clear_downloads()

        threading.Thread(target=process_user_last_url_search, args=(call.message.chat.id, target_url, status_msg)).start()
        return

    if data.startswith("mc_"):
        music_choices = load_json(MUSIC_CHOICES_FILE, {})
        m_url = music_choices.get(data)

        if not m_url:
            bot.answer_callback_query(call.id, "❌ این لینک منقضی شده است. مجدداً تلاش کنید.", show_alert=True)
            return

        bot.answer_callback_query(call.id, "📥 در حال دانلود موزیک...")
        status_msg = bot.send_message(call.message.chat.id, "📥 دانلود موزیک: 0%")

        last_update_time = [0]
        def music_progress_hook(d):
            if d['status'] == 'downloading':
                pct = d.get('_percent_str', '0%').strip()
                current_time = time.time()
                if current_time - last_update_time[0] > 1.5:
                    last_update_time[0] = current_time
                    try:
                        bot.edit_message_text(f"📥 دانلود موزیک: {pct}", call.message.chat.id, status_msg.message_id)
                    except:
                        pass

        def download_and_send_selected_music(chat_id, music_url, msg_to_del):
            try:
                music_dl_opts = {
                    'format': 'bestaudio',
                    'outtmpl': f'{DOWNLOAD_DIR}/selected_music_%(id)s.%(ext)s',
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                    'quiet': True, 'noplaylist': True,
                    'progress_hooks': [music_progress_hook]
                }
                final_music_path = None
                with yt_dlp.YoutubeDL(music_dl_opts) as music_ydl:
                    info_dl = music_ydl.extract_info(music_url, download=True)
                    final_music_path = music_ydl.prepare_filename(info_dl).rsplit('.', 1)[0] + '.mp3'

                if final_music_path and os.path.exists(final_music_path):
                    bot.edit_message_text("📤 در حال ارسال موزیک: 100%", chat_id, msg_to_del.message_id)
                    with open(final_music_path, 'rb') as aud:
                        bot.send_audio(chat_id, aud, caption="🎵 موزیک کامل و واقعی شما (100%)\n🤖 t.me/zeucdl_bot")
                    bot.delete_message(chat_id, msg_to_del.message_id)
                else:
                    bot.edit_message_text("⚠️ خطا در دریافت فایل صوتی موزیک.", chat_id, msg_to_del.message_id)
            except Exception as ex:
                try: bot.edit_message_text(f"❌ خطا: {str(ex)}", chat_id, msg_to_del.message_id)
                except: pass
            finally:
                clear_downloads()

        threading.Thread(target=download_and_send_selected_music, args=(call.message.chat.id, m_url, status_msg)).start()
        return

    if user_id in admins:
        if data.startswith("adm_users_page_"):
            parts = data.replace("adm_users_page_", "").split("_", 1)
            p = int(parts[0])
            sq = parts[1] if len(parts) > 1 else ""
            txt, mrk = generate_users_page(p, sq)
            bot.answer_callback_query(call.id)
            bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=mrk)
            return

        elif data == "adm_users_mgmt":
            txt, mrk = generate_users_page(0, "")
            bot.answer_callback_query(call.id)
            bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=mrk)
            return

        elif data == "adm_users_search":
            user_states[user_id] = "waiting_user_search_query"
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "🔍 لطفاً آیدی (Username) یا آیدی عددی (ID) کاربر مورد نظر را برای جستجو ارسال کنید:")
            return

        elif data.startswith("adm_usr_opt_"):
            target_uid = data.replace("adm_usr_opt_", "")
            users = load_users()
            udata = users.get(target_uid, {})
            name = udata.get("first_name", "بدون نام")
            uname = udata.get("username", "ندارد")
            expire = udata.get("subscription_expire", 0)
            now = time.time()

            sub_info = f"🔴 بدون اشتراک"
            if expire > now:
                days_left = int((expire - now) / 86400)
                sub_info = f"🟢 فعال ({days_left} روز باقی‌مانده)"

            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("🟢 فعال‌سازی اشتراک ۱ ماهه (۳۰ روز)", callback_data=f"sub_grant_{target_uid}_30"),
                types.InlineKeyboardButton("🟢 فعال‌سازی اشتراک ۲ ماهه (۶۰ روز)", callback_data=f"sub_grant_{target_uid}_60"),
                types.InlineKeyboardButton("🟢 فعال‌سازی اشتراک ۱ ساله (۳۶۵ روز)", callback_data=f"sub_grant_{target_uid}_365"),
                types.InlineKeyboardButton("🔴 سلب اشتراک (حذف اشتراک)", callback_data=f"sub_revoke_{target_uid}"),
                types.InlineKeyboardButton("🔙 بازگشت به لیست کاربران", callback_data="adm_users_mgmt")
            )
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                f"👤 **مدیریت اشتراک کاربر:**\n\n"
                f"▪️ نام: {name}\n"
                f"▪️ یوزرنیم: @{uname}\n"
                f"▪️ آیدی عددی: `{target_uid}`\n"
                f"▪️ وضعیت اشتراک: {sub_info}",
                call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown"
            )
            return

        elif data.startswith("sub_grant_"):
            parts = data.replace("sub_grant_", "").split("_")
            target_uid = parts[0]
            days = int(parts[1])
            
            users = load_users()
            if target_uid in users:
                now = time.time()
                current_expire = users[target_uid].get("subscription_expire", 0)
                base_time = max(now, current_expire) if current_expire > now else now
                new_expire = base_time + (days * 86400)
                
                users[target_uid]["subscription_expire"] = new_expire
                save_json(USERS_FILE, users)
                
                bot.answer_callback_query(call.id, f"✅ اشتراک {days} روزه با موفقیت فعال شد!", show_alert=True)
                
                udata = users[target_uid]
                name = udata.get("first_name", "بدون نام")
                uname = udata.get("username", "ندارد")
                days_left = int((new_expire - now) / 86400)
                
                markup = types.InlineKeyboardMarkup(row_width=1)
                markup.add(
                    types.InlineKeyboardButton("🟢 فعال‌سازی اشتراک ۱ ماهه (۳۰ روز)", callback_data=f"sub_grant_{target_uid}_30"),
                    types.InlineKeyboardButton("🟢 فعال‌سازی اشتراک ۲ ماهه (۶۰ روز)", callback_data=f"sub_grant_{target_uid}_60"),
                    types.InlineKeyboardButton("🟢 فعال‌سازی اشتراک ۱ ساله (۳۶۵ روز)", callback_data=f"sub_grant_{target_uid}_365"),
                    types.InlineKeyboardButton("🔴 سلب اشتراک (حذف اشتراک)", callback_data=f"sub_revoke_{target_uid}"),
                    types.InlineKeyboardButton("🔙 بازگشت به لیست کاربران", callback_data="adm_users_mgmt")
                )
                bot.edit_message_text(
                    f"👤 **مدیریت اشتراک کاربر:**\n\n"
                    f"▪️ نام: {name}\n"
                    f"▪️ یوزرنیم: @{uname}\n"
                    f"▪️ آیدی عددی: `{target_uid}`\n"
                    f"▪️ وضعیت اشتراک: 🟢 فعال ({days_left} روز باقی‌مانده)",
                    call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown"
                )
            return

        elif data.startswith("sub_revoke_"):
            target_uid = data.replace("sub_revoke_", "")
            users = load_users()
            if target_uid in users:
                users[target_uid]["subscription_expire"] = 0
                save_json(USERS_FILE, users)
                
                bot.answer_callback_query(call.id, "❌ اشتراک کاربر با موفقیت سلب (حذف) شد!", show_alert=True)
                
                udata = users[target_uid]
                name = udata.get("first_name", "بدون نام")
                uname = udata.get("username", "ندارد")
                
                markup = types.InlineKeyboardMarkup(row_width=1)
                markup.add(
                    types.InlineKeyboardButton("🟢 فعال‌سازی اشتراک ۱ ماهه (۳۰ روز)", callback_data=f"sub_grant_{target_uid}_30"),
                    types.InlineKeyboardButton("🟢 فعال‌سازی اشتراک ۲ ماهه (۶۰ روز)", callback_data=f"sub_grant_{target_uid}_60"),
                    types.InlineKeyboardButton("🟢 فعال‌سازی اشتراک ۱ ساله (۳۶۵ روز)", callback_data=f"sub_grant_{target_uid}_365"),
                    types.InlineKeyboardButton("🔴 سلب اشتراک (حذف اشتراک)", callback_data=f"sub_revoke_{target_uid}"),
                    types.InlineKeyboardButton("🔙 بازگشت به لیست کاربران", callback_data="adm_users_mgmt")
                )
                bot.edit_message_text(
                    f"👤 **مدیریت اشتراک کاربر:**\n\n"
                    f"▪️ نام: {name}\n"
                    f"▪️ یوزرنیم: @{uname}\n"
                    f"▪️ آیدی عددی: `{target_uid}`\n"
                    f"▪️ وضعیت اشتراک: 🔴 بدون اشتراک",
                    call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown"
                )
            return

    if user_id not in admins:
        bot.answer_callback_query(call.id, "❌ دسترسی غیرمجاز!", show_alert=True)
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
        bot.send_message(call.message.chat.id, "📢 آیدی کانال را بفرستید مثل `@channel`:")

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
        bot.edit_message_text(f"🤖 **مدیریت ربات‌های ساخته شده:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

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
            if b_token in child_bot_instances:
                try: child_bot_instances[b_token].stop_polling()
                except: pass
                child_bot_instances.pop(b_token, None)
            del child_bots[b_token]
            save_child_bots(child_bots)
            bot.answer_callback_query(call.id, "✅ ربات حذف شد!", show_alert=True)
            bot.edit_message_text("🤖 **مدیریت ربات‌های ساخته شده:**", call.message.chat.id, call.message.message_id)

    elif data == "adm_buttons_mgmt":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✏️ تغییر نام دکمه‌ها", callback_data="adm_rename_btn"),
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

    elif data.startswith("rename_"):
        btn_key = data.replace("rename_", "")
        user_states[user_id] = f"set_name_{btn_key}"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "✍️ نام جدید دکمه را بفرستید:")

    elif data == "adm_back":
        if user_id not in admins: return
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📊 آمار کاربران", callback_data="adm_stats"),
            types.InlineKeyboardButton("📢 ارسال همگانی", callback_data="adm_broadcast"),
            types.InlineKeyboardButton("📢 مدیریت کانال‌های قفل", callback_data="adm_channels_mgmt"),
            types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="adm_users_mgmt"),
            types.InlineKeyboardButton("🤖 مدیریت ربات‌های ساخته شده", callback_data="adm_child_bots_mgmt"),
            types.InlineKeyboardButton("🎛 مدیریت دکمه‌ها", callback_data="adm_buttons_mgmt")
        )
        bot.edit_message_text("🛠 **پنل مدیریت پیشرفته ربات:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.message_handler(content_types=['text', 'document'])
def handle_all_requests(message):
    user_id = message.from_user.id
    settings = load_settings()
    admins = settings.get("admins", INITIAL_ADMINS)

    if is_banned(user_id): return
    save_user(message)
    channels = settings.get("channels", [])

    is_guest = (user_states.get(user_id) == "guest_mode")

    if channels and user_id not in admins and not check_membership(user_id):
        bot.reply_to(message, "⚠️ لطفا ابتدا در کانال‌های ربات عضو شوید.")
        return

    text = ""
    if message.document:
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            text = downloaded_file.decode('utf-8')
        except:
            text = message.text.strip() if message.text else ""
    else:
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
                types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="adm_users_mgmt"),
                types.InlineKeyboardButton("🤖 مدیریت ربات‌های ساخته شده", callback_data="adm_child_bots_mgmt"),
                types.InlineKeyboardButton("🎛 مدیریت دکمه‌ها", callback_data="adm_buttons_mgmt")
            )
            bot.reply_to(message, "🛠 **پنل مدیریت پیشرفته ربات:**", reply_markup=markup)
            return

        elif current_state == "waiting_user_search_query":
            user_states.pop(user_id, None)
            sq = text.strip()
            txt, mrk = generate_users_page(0, sq)
            bot.reply_to(message, f"🔍 **نتیجه جستجو برای:** `{sq}`", reply_markup=mrk, parse_mode="Markdown")
            return

        elif current_state and current_state.startswith("set_name_"):
            btn_key = current_state.replace("set_name_", "")
            settings["btn_names"][btn_key] = text
            save_settings(settings)
            bot.reply_to(message, f"✅ نام دکمه تغییر کرد!", reply_markup=get_reply_keyboard(user_id))
            user_states.pop(user_id, None)
            return

    if text == "👨‍💻 سازنده" or text == "سازنده":
        bot.reply_to(message, "🤖 **این ربات با سیستم پیشرفته ساخت ربات ساخته شده است.**\n\n📌 سازنده و پشتیبان اصلی:\n@izeucs", reply_markup=get_reply_keyboard(user_id))
        return

    if text == btn_names.get("builder", "ساخت ربات دانلودر"):
        if has_active_subscription(user_id):
            user_states[user_id] = "waiting_bot_token"
            bot.reply_to(message, "🤖 **ساخت ربات دانلودر اختصاصی:**\n\nاشتراک شما فعال است! لطفاً توکن ربات خود را از `@BotFather` بفرستید:", reply_markup=get_reply_keyboard(user_id))
        else:
            bot.reply_to(
                message,
                "برای استفاده از این دکمه و ساخت ربات اختصاصی خودتون به ایدی زیر پیام بدید:\n\n"
                "هزینه یک ماه اشتراک این دکمه 100 هزارتومان\n\n"
                "ایدی جهت خرید:\n@izeucs",
                reply_markup=get_reply_keyboard(user_id)
            )
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
        status_msg = bot.reply_to(message, "⏳ در حال دریافت سرور رندوم V2Ray (0%)...")
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
                bot.reply_to(message, f"🌐 **سرور رایگان V2Ray (100%):**\n\n`{selected_config}`", parse_mode="Markdown", reply_markup=get_reply_keyboard(user_id))
            else:
                bot.edit_message_text("❌ سروری یافت نشد (100%).", message.chat.id, status_msg.message_id)
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

    # ذخیره آخرین لینک ارسالی کاربر برای استفاده در جستجوی موزیک
    user_last_urls = load_json(USER_LAST_URL_FILE, {})
    user_last_urls[str(user_id)] = text
    save_json(USER_LAST_URL_FILE, user_last_urls)

    def process_instagram_link(chat_id, url, user_st_key):
        status_msg = bot.send_message(chat_id, "📥 دانلود ویدیو: 0%")
        
        last_update_time = [0]
        def download_progress_hook(d):
            if d['status'] == 'downloading':
                pct = d.get('_percent_str', '0%').strip()
                current_time = time.time()
                if current_time - last_update_time[0] > 1.5:
                    last_update_time[0] = current_time
                    try:
                        bot.edit_message_text(f"📥 دانلود ویدیو: {pct}", chat_id, status_msg.message_id)
                    except:
                        pass

        try:
            ydl_opts = {
                'format': 'best',
                'outtmpl': f'{DOWNLOAD_DIR}/t.me_zeucdl_bot_%(id)s.%(ext)s',
                'quiet': True,
                'progress_hooks': [download_progress_hook]
            }
            
            video_file_path = None

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                base_path = ydl.prepare_filename(info).rsplit('.', 1)[0]
                video_file_path = base_path + '.mp4'
                if not os.path.exists(video_file_path):
                    video_file_path = base_path + '.mkv'

            if video_file_path and os.path.exists(video_file_path):
                post_key = str(abs(hash(url + str(time.time()))))
                posts_cache = load_json(POSTS_CACHE_FILE, {})
                posts_cache[post_key] = url
                if len(posts_cache) > 200:
                    posts_cache.pop(list(posts_cache.keys())[0])
                save_json(POSTS_CACHE_FILE, posts_cache)

                markup = types.InlineKeyboardMarkup(row_width=1)
                markup.add(
                    types.InlineKeyboardButton("🎵 شناسایی موسیقی از روی صدا", callback_data=f"find_music_{post_key}"),
                    types.InlineKeyboardButton("🔗 اشتراک‌گذاری پست", url=url)
                )

                bot.edit_message_text("📤 در حال ارسال به آرشیو کانال (50%)...", chat_id, status_msg.message_id)

                try:
                    with open(video_file_path, 'rb') as vid:
                        bot.send_video(ARCHIVE_CHANNEL, vid, caption=f"✅ ویدیو آرشیو شده (100%).\n\n🤖 t.me/zeucdl_bot", reply_markup=markup)
                except Exception as ch_err:
                    print(f"Archive channel error: {ch_err}")

                with open(video_file_path, 'rb') as vid:
                    bot.send_video(chat_id, vid, caption=f"✅ ویدیو دانلود شد (100%).\n\n🤖 t.me/zeucdl_bot", reply_markup=markup)

                bot.delete_message(chat_id, status_msg.message_id)
        except Exception as e:
            try: bot.edit_message_text(f"❌ خطا: {str(e)}", chat_id, status_msg.message_id)
            except: pass
        finally:
            user_states.pop(user_st_key, None)
            clear_downloads()

    if current_state == "waiting_insta" or "instagram.com" in text:
        threading.Thread(target=process_instagram_link, args=(message.chat.id, text, user_id)).start()
        return

    elif current_state == "waiting_music" or "spotify.com" in text or "soundcloud.com" in text:
        status_msg = bot.send_message(message.chat.id, "🎵 دانلود موزیک: 0%")
        target_url = text
        if "spotify.com" in text:
            try:
                req = urllib.request.Request(text, headers={'User-Agent': 'Mozilla/5.0'})
                html = urllib.request.urlopen(req).read().decode('utf-8')
                m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                if m: target_url = f"scsearch:{m.group(1)}"
            except: pass

        last_update_time = [0]
        def music_dl_hook(d):
            if d['status'] == 'downloading':
                pct = d.get('_percent_str', '0%').strip()
                current_time = time.time()
                if current_time - last_update_time[0] > 1.5:
                    last_update_time[0] = current_time
                    try:
                        bot.edit_message_text(f"🎵 دانلود موزیک: {pct}", message.chat.id, status_msg.message_id)
                    except:
                        pass

        ydl_opts = {
            'format': 'bestaudio',
            'outtmpl': f'{DOWNLOAD_DIR}/t.me_zeucdl_bot_%(id)s.%(ext)s',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'quiet': True, 'noplaylist': True,
            'progress_hooks': [music_dl_hook]
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=True)
            if 'entries' in info: info = info['entries'][0]
            file_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
        if os.path.exists(file_path):
            bot.edit_message_text("📤 در حال ارسال موزیک (100%)...", message.chat.id, status_msg.message_id)
            with open(file_path, 'rb') as audio:
                bot.send_audio(message.chat.id, audio, caption="🎵 موزیک دانلود شده (100%)\n🤖 t.me/zeucdl_bot")
            bot.delete_message(message.chat.id, status_msg.message_id)
        user_states.pop(user_id, None)
        clear_downloads()
        return

def run_child_bot(token):
    try:
        c_bot = telebot.TeleBot(token)
        child_bot_instances[token] = c_bot
        
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
            if token not in cbots: return
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
            if token not in cbots: return
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
                status = c_bot.reply_to(msg, "📥 دانلود ویدیو: 0%")
                try:
                    def child_dl_hook(d):
                        if d['status'] == 'downloading':
                            pct = d.get('_percent_str', '0%').strip()
                            try: c_bot.edit_message_text(f"📥 دانلود ویدیو: {pct}", msg.chat.id, status.message_id)
                            except: pass

                    ydl_opts = {'format': 'best', 'outtmpl': f'{DOWNLOAD_DIR}/child_%(id)s.%(ext)s', 'quiet': True, 'progress_hooks': [child_dl_hook]}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(txt, download=True)
                        f_path = ydl.prepare_filename(info)
                        if not os.path.exists(f_path): f_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp4'
                    if os.path.exists(f_path):
                        c_bot.edit_message_text("📤 در حال ارسال (100%)...", msg.chat.id, status.message_id)
                        with open(f_path, 'rb') as f_vid:
                            c_bot.send_video(msg.chat.id, f_vid, caption="✅ دانلود انجام شد (100%).")
                        c_bot.delete_message(msg.chat.id, status.message_id)
                except Exception as e:
                    c_bot.edit_message_text(f"❌ خطا: {str(e)}", msg.chat.id, status.message_id)
            else:
                c_bot.reply_to(msg, "لطفاً یک لینک معتبر ارسال کنید.")

        c_bot.remove_webhook()
        c_bot.infinity_polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"Child bot error for token {token[:8]}...: {e}")

def start_child_bot(token):
    t = threading.Thread(target=run_child_bot, args=(token,))
    t.daemon = True
    child_bot_threads[token] = t
    t.start()

def init_saved_child_bots():
    child_bots = load_child_bots()
    for token in child_bots.keys():
        start_child_bot(token)

if __name__ == "__main__":
    init_saved_child_bots()
    
    fetch_thread = threading.Thread(target=fetch_channel_web_updates)
    fetch_thread.daemon = True
    fetch_thread.start()

    web_thread = threading.Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()

    ping_thread = threading.Thread(target=self_ping_worker)
    ping_thread.daemon = True
    ping_thread.start()
    
    print("Bot & Web server are running with Self-Ping enabled...")
    try: bot.remove_webhook()
    except: pass
    bot.infinity_polling()
