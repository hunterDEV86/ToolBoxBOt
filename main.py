import subprocess
import sys


def install_requirements():
    required_packages = [
        'pyTelegramBotAPI', 'flask', 'requests', 'python-dotenv', 'aiohttp',
        'asyncio', 'uvicorn', 'fastapi', 'django', 'websockets', 'os'
    ]

    for package in required_packages:
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} installed successfully")
        except:
            print(f"❌ Failed to install {package}")


# Install packages when script starts
if __name__ == '__main__':
    print("📦 Installing required packages...")
    install_requirements()

import telebot
from telebot import types
import sys
import os
from io import StringIO
import contextlib
import threading
import time
from queue import Queue
import main1
from keep_alive import keep_alive
import xo_game
import othello_game

keep_alive()

# Initialize bot with your token
bot = telebot.TeleBot("7264390282:AAGbnTa8u6SRqxJpaiyhnMBpTYVc5KvrC7s")

# Dictionary to store user states and running codes
user_coding_state = {}
running_codes = {}
user_panels = {}
permanent_codes = {}
MAX_CONCURRENT_CODES = 5
CODE_TIMEOUT = 120  # 2 minutes
DELETE_TIMEOUT = 30  # 30 seconds for message deletion
ADMIN_LIST = ['username1', 'username2']  # Add admin usernames here (without @)
REPLIT_DOMAIN = "https://67f4f76e-9e9c-4299-b5c9-60f512a1432b-00-32zk82shfh1ws.pike.replit.dev"


def delete_command_messages(chat_id, command_message_id, bot_response_id):
    try:
        threading.Timer(
            DELETE_TIMEOUT,
            lambda: bot.delete_message(chat_id, command_message_id)).start()
        threading.Timer(
            DELETE_TIMEOUT,
            lambda: bot.delete_message(chat_id, bot_response_id)).start()
    except:
        pass


def execute_with_timeout(code,
                         message_id,
                         chat_id,
                         original_message,
                         is_permanent=False):
    # بهبود تشخیص وب سرور با کلمات کلیدی بیشتر
    web_server_keywords = [
        'app.run', 'runserver', 'serve_forever', 'Flask(', 'flask.Flask',
        '@app.route', 'FastAPI(', 'uvicorn.run', 'django', 'web.run_app'
    ]

    is_web_server = any(keyword in code for keyword in web_server_keywords)
    server_port = '5000'  # پورت پیش‌فرض

    # استخراج پورت از کد با پشتیبانی از فرمت‌های مختلف
    port_patterns = ['port=', 'PORT=', ':']
    for pattern in port_patterns:
        if pattern in code:
            try:
                port_start = code.index(pattern) + len(pattern)
                port_end = code.find(')', port_start)
                if port_end == -1:
                    port_end = code.find(',', port_start)
                if port_end == -1:
                    port_end = code.find('\n', port_start)
                if port_end != -1:
                    extracted_port = code[port_start:port_end].strip()
                    if extracted_port.isdigit():
                        server_port = extracted_port
            except:
                pass

    # چک کردن دسترسی به os برای مدیران
    if ("os" in code or "import os"
            in code) and original_message.from_user.username not in ADMIN_LIST:
        sent_message = bot.reply_to(
            original_message,
            "⛔️ استفاده از کتابخانه os فقط برای مدیران مجاز است!")
        delete_command_messages(chat_id, original_message.message_id,
                                sent_message.message_id)
        return

    stdout = StringIO()
    with contextlib.redirect_stdout(stdout):
        try:
            exec(code)
            output = stdout.getvalue()

            # ارسال پیام با URL سرور
            if is_web_server:
                server_url = f"{REPLIT_DOMAIN}:{server_port}"
                bot.send_message(
                    chat_id,
                    f"🌐 سرور وب راه‌اندازی شد!\nURL: `{server_url}`",
                    parse_mode='Markdown')

            if output:
                output = output.replace('_', '\\_')
                sent_message = bot.send_message(
                    chat_id,
                    f"✅ خروجی کد:\n```\n{output}\n```",
                    parse_mode='Markdown')
            else:
                sent_message = bot.send_message(
                    chat_id, "✅ کد با موفقیت اجرا شد (بدون خروجی)")

            if not is_permanent:
                delete_command_messages(chat_id, original_message.message_id,
                                        sent_message.message_id)

        except Exception as e:
            error_msg = str(e).replace('_', '\\_')
            sent_message = bot.send_message(
                chat_id,
                f"❌ خطا در اجرای کد:\n```\n{error_msg}\n```",
                parse_mode='Markdown')
            if not is_permanent:
                delete_command_messages(chat_id, original_message.message_id,
                                        sent_message.message_id)

    if message_id in running_codes:
        del running_codes[message_id]

@bot.message_handler(commands=['calc'])
def handle_calc(message):
    try:
        # دریافت فرمول از کاربر
        formula = message.text.split(' ', 1)[1]

        # محاسبه و رسم نمودار
        response, plot_buf = calculate_and_plot(formula)

        # ارسال پاسخ به صورت عکس
        if isinstance(plot_buf, io.BytesIO):
            bot.send_photo(message.chat.id, plot_buf)
            bot.reply_to(message, response)  # ارسال پاسخ به صورت متن
        else:
            bot.send_photo(message.chat.id, plot_buf)

    except Exception as e:
        error_message = f"خطا: {str(e)}"
        image_buf = create_image_from_text(error_message)
        bot.send_photo(message.chat.id, image_buf)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
🤖 به ربات اجرای کد پایتون خوش آمدید!

برای شروع کار از دستور /panel استفاده کنید
    """
    sent = bot.reply_to(message, welcome_text)
    delete_command_messages(message.chat.id, message.message_id,
                            sent.message_id)


@bot.message_handler(commands=['codefor'])
def run_permanent_code(message):
    if message.from_user.username not in ADMIN_LIST:
        bot.reply_to(message, "⛔️ این دستور فقط برای مدیران مجاز است!")
        return

    markup = types.ForceReply(selective=True)
    sent = bot.send_message(
        message.chat.id,
        "💻 کد دائمی خود را وارد کنید:\n_(برای لغو، /cancel را بفرستید)_",
        reply_markup=markup,
        parse_mode='Markdown')
    user_coding_state[sent.message_id] = message.from_user.id


@bot.message_handler(commands=['stopcode'])
def stop_permanent_code(message):
    if message.from_user.username not in ADMIN_LIST:
        bot.reply_to(message, "⛔️ این دستور فقط برای مدیران مجاز است!")
        return

    if not permanent_codes:
        bot.reply_to(message, "❌ هیچ کد دائمی در حال اجرا نیست!")
        return

    for code_id in list(permanent_codes.keys()):
        thread = permanent_codes[code_id]
        if thread.is_alive():
            thread._stop()
        del permanent_codes[code_id]

    bot.reply_to(message, "✅ تمام کدهای دائمی متوقف شدند.")


@bot.message_handler(commands=['panel'])
def show_panel(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    run_code_btn = types.InlineKeyboardButton("🚀 اجرای کد",
                                              callback_data="run_code")
    status_btn = types.InlineKeyboardButton("📊 وضعیت سیستم",
                                            callback_data="status")
    close_panel_btn = types.InlineKeyboardButton("❌ بستن پنل",
                                                 callback_data="close_panel")
    markup.add(run_code_btn, status_btn, close_panel_btn)

    sent = bot.send_message(message.chat.id,
                            "📱 پنل کاربری:",
                            reply_markup=markup)
    user_panels[user_id] = sent.message_id
    delete_command_messages(message.chat.id, message.message_id,
                            sent.message_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data.startswith('othello_'):
        othello_game.handle_callback(bot, call)
        return
    elif call.data.startswith('xo_'):
        xo_game.handle_callback(bot, call)
        return
    
    # بقیه منطق panel
    user_id = call.from_user.id
    if call.data == "run_code":
        if len(running_codes) >= MAX_CONCURRENT_CODES:
            bot.answer_callback_query(call.id,
                                      "⚠️ سیستم در حال حاضر مشغول است")
            return
        markup = types.ForceReply(selective=True)
        sent = bot.send_message(
            call.message.chat.id,
            "💻 کد پایتون خود را وارد کنید:\n_(برای لغو، /cancel را بفرستید)_",
            reply_markup=markup,
            parse_mode='Markdown')
        user_coding_state[sent.message_id] = user_id
        # پاک کردن پیام قبلی کاربر
        bot.delete_message(call.message.chat.id, call.message.message_id)
    elif call.data == "status":
        running_count = len(running_codes)
        permanent_count = len(permanent_codes)
        status_text = f"""
📊 وضعیت سیستم:
• کدهای در حال اجرا: {running_count}
• کدهای دائمی: {permanent_count}
• حداکثر ظرفیت: {MAX_CONCURRENT_CODES}
• زمان مجاز اجرا: {CODE_TIMEOUT} ثانیه
        """
        bot.answer_callback_query(call.id, status_text, show_alert=True)
    elif call.data == "close_panel":
        username = call.from_user.username
        if username in ADMIN_LIST:
            user_panels.clear()
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, "تمام پنل‌ها بسته شدند")
        elif user_id in user_panels:
            del user_panels[user_id]
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, "پنل بسته شد")

#@bot.message_handler(commands=['go'])
#def start_go(message):
 #   go_game.start_game(bot, message)

@bot.message_handler(commands=['cancel'])
def cancel_coding(message):
    if message.from_user.id not in user_panels:
        bot.delete_message(message.chat.id, message.message_id)
        return

    if message.reply_to_message and message.reply_to_message.message_id in user_coding_state:
        del user_coding_state[message.reply_to_message.message_id]
        sent = bot.reply_to(message, "❌ عملیات لغو شد.")
        delete_command_messages(message.chat.id, message.message_id,
                                sent.message_id)


@bot.message_handler(commands=['xo'])
def start_xo(message):
    xo_game.start_game(bot, message)



@bot.message_handler(commands=['othello'])
def start_othello(message):
    bot.send_message(message.chat.id, "🎲 بازی اوتلو")
    othello_game.show_game_menu(bot, message)  # تغییر به فراخوانی منوی جدید


# اضافه کردن import در بالای فایل

# اضافه کردن به callback handler موجود
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data.startswith(('othello_mode_', 'othello_join_', 'othello_')):
        othello_game.handle_callback(bot, call)
        return
    # بقیه کد callback handler...
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if message.text.startswith('/'):
        return

    if not message.reply_to_message:
        return

    if message.reply_to_message.message_id in user_coding_state:
        if message.from_user.id != user_coding_state[
                message.reply_to_message.message_id]:
            sent = bot.reply_to(message, "⛔️ شما مجاز به اجرای این کد نیستید.")
            delete_command_messages(message.chat.id, message.message_id,
                                    sent.message_id)
            return

        # اگر پیام ریپلای به دستور codefor باشد
        if message.reply_to_message.text.startswith("💻 کد دائمی"):
            if message.from_user.username not in ADMIN_LIST:
                bot.reply_to(message,
                             "⛔️ این عملیات فقط برای مدیران مجاز است!")
                return

            code = message.text
            thread = threading.Thread(target=execute_with_timeout,
                                      args=(code, message.message_id,
                                            message.chat.id, message, True),
                                      daemon=True)

            permanent_codes[message.message_id] = thread
            thread.start()

            bot.reply_to(
                message,
                f"✅ کد دائمی شما با شناسه `{message.message_id}` شروع به اجرا کرد.",
                parse_mode='Markdown')
            del user_coding_state[message.reply_to_message.message_id]
            return

        if len(
                running_codes
        ) >= MAX_CONCURRENT_CODES and message.message_id not in permanent_codes:
            sent = bot.reply_to(
                message, "⚠️ سیستم در حال حاضر مشغول است. لطفا کمی صبر کنید.")
            delete_command_messages(message.chat.id, message.message_id,
                                    sent.message_id)
            return

        code = message.text
        thread = threading.Thread(target=execute_with_timeout,
                                  args=(code, message.message_id,
                                        message.chat.id, message))

        running_codes[message.message_id] = thread
        thread.daemon = True
        thread.start()

        timer = threading.Timer(
            CODE_TIMEOUT,
            lambda: stop_code(message.message_id, message.chat.id))
        timer.start()

        sent_message = bot.reply_to(
            message,
            f"🔄 کد شما در حال اجراست...\n• شناسه: `{message.message_id}`\n• زمان مجاز: {CODE_TIMEOUT} ثانیه",
            parse_mode='Markdown')
        delete_command_messages(message.chat.id, message.message_id,
                                sent_message.message_id)

        del user_coding_state[message.reply_to_message.message_id]


def stop_code(message_id, chat_id):
    if message_id in running_codes:
        del running_codes[message_id]
        sent_message = bot.send_message(
            chat_id,
            f"⏱ کد با شناسه {message_id} به دلیل اتمام زمان متوقف شد.")
        threading.Timer(
            DELETE_TIMEOUT, lambda: bot.delete_message(chat_id, sent_message.
                                                       message_id)).start()


@bot.message_handler(commands=['sto'])
def ss(message):
    main1.test(bot, message)


# اضافه کردن import


# اضافه کردن handler جدید



# اضافه کردن دستور به لیست دستورات
bot.set_my_commands([
    telebot.types.BotCommand("/start", "شروع مجدد ربات"),
    telebot.types.BotCommand("/panel", "نمایش پنل کاربری"),
    telebot.types.BotCommand("/cancel", "لغو عملیات فعلی"),
    telebot.types.BotCommand("/codefor", "اجرای کد دائمی (فقط مدیران)"),
    telebot.types.BotCommand("/stopcode", "توقف کدهای"),
    telebot.types.BotCommand("/xo", "شروع بازی XO"),
    telebot.types.BotCommand("/othello", "شروع بازی اوتلو"),
    telebot.types.BotCommand("/go", "شروع بازی گو")
])

# Start the bot
bot.infinity_polling()
