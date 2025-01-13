import io
import subprocess
import sys

from calculator import calculate_and_plot, create_image_from_text


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

import io
import subprocess
import sys
from calculator import calculate_and_plot, create_image_from_text
import telebot
from telebot import types
import os
from io import StringIO
import contextlib
import threading
import time
from queue import Queue
from keep_alive import keep_alive
import xo_game
import othello_game
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
keep_alive()

# Initialize bot with your token
bot = telebot.TeleBot(os.environ['token'])

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


def update_message_real_time(chat_id, message_id, output_queue):
    output_text = ""
    while True:
        if not output_queue.empty():
            new_output = output_queue.get()
            output_text += new_output + "\n"
            try:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"🔄 کد در حال اجرا...\n```\n{output_text}\n```",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error updating message: {e}")
        time.sleep(1)  # هر 1 ثانیه پیام را به‌روز کنید


def execute_with_timeout(code, message_id, chat_id, original_message, is_permanent=False):
    output_queue = Queue()
    update_thread = threading.Thread(
        target=update_message_real_time,
        args=(chat_id, message_id, output_queue),
        daemon=True
    )
    update_thread.start()

    stdout = StringIO()
    with contextlib.redirect_stdout(stdout):
        try:
            exec(code)
            output = stdout.getvalue()
            output_queue.put(output)  # ارسال خروجی به صف

            if is_web_server:
                server_url = f"{REPLIT_DOMAIN}:{server_port}"
                bot.send_message(
                    chat_id,
                    f"🌐 سرور وب راه‌اندازی شد!\nURL: `{server_url}`",
                    parse_mode='Markdown'
                )

            if output:
                output = output.replace('_', '\\_')
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"✅ خروجی کد:\n```\n{output}\n```",
                    parse_mode='Markdown'
                )
            else:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="✅ کد با موفقیت اجرا شد (بدون خروجی)"
                )

        except Exception as e:
            error_msg = str(e).replace('_', '\\_')
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"❌ خطا در اجرای کد:\n```\n{error_msg}\n```",
                parse_mode='Markdown'
            )

    if message_id in running_codes:
        del running_codes[message_id]


@bot.message_handler(commands=['calc'])
def handle_calc(message):
    try:
        formula = message.text.split(' ', 1)[1]
        response, plot_buf = calculate_and_plot(formula)
        if isinstance(plot_buf, io.BytesIO):
            bot.send_photo(message.chat.id, plot_buf)
            bot.reply_to(message, response)
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
    delete_command_messages(message.chat.id, message.message_id, sent.message_id)


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
        parse_mode='Markdown'
    )
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
    run_code_btn = types.InlineKeyboardButton("🚀 اجرای کد", callback_data="run_code")
    status_btn = types.InlineKeyboardButton("📊 وضعیت سیستم", callback_data="status")
    close_panel_btn = types.InlineKeyboardButton("❌ بستن پنل", callback_data="close_panel")
    markup.add(run_code_btn, status_btn, close_panel_btn)

    sent = bot.send_message(message.chat.id, "📱 پنل کاربری:", reply_markup=markup)
    user_panels[user_id] = sent.message_id
    delete_command_messages(message.chat.id, message.message_id, sent.message_id)


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data.startswith('othello_'):
        othello_game.handle_callback(bot, call)
        return
    elif call.data.startswith('xo_'):
        xo_game.handle_callback(bot, call)
        return

    user_id = call.from_user.id
    if call.data == "run_code":
        if len(running_codes) >= MAX_CONCURRENT_CODES:
            bot.answer_callback_query(call.id, "⚠️ سیستم در حال حاضر مشغول است")
            return
        markup = types.ForceReply(selective=True)
        sent = bot.send_message(
            call.message.chat.id,
            "💻 کد پایتون خود را وارد کنید:\n_(برای لغو، /cancel را بفرستید)_",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        user_coding_state[sent.message_id] = user_id
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


@bot.message_handler(commands=['cancel'])
def cancel_coding(message):
    if message.from_user.id not in user_panels:
        bot.delete_message(message.chat.id, message.message_id)
        return

    if message.reply_to_message and message.reply_to_message.message_id in user_coding_state:
        del user_coding_state[message.reply_to_message.message_id]
        sent = bot.reply_to(message, "❌ عملیات لغو شد.")
        delete_command_messages(message.chat.id, message.message_id, sent.message_id)


@bot.message_handler(commands=['xo'])
def start_xo(message):
    xo_game.start_game(bot, message)


@bot.message_handler(commands=['othello'])
def start_othello(message):
    bot.send_message(message.chat.id, "🎲 بازی اوتلو")
    othello_game.show_game_menu(bot, message)


@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if message.text.startswith('/'):
        return

    if not message.reply_to_message:
        return

    if message.reply_to_message.message_id in user_coding_state:
        if message.from_user.id != user_coding_state[message.reply_to_message.message_id]:
            sent = bot.reply_to(message, "⛔️ شما مجاز به اجرای این کد نیستید.")
            delete_command_messages(message.chat.id, message.message_id, sent.message_id)
            return

        if len(running_codes) >= MAX_CONCURRENT_CODES and message.message_id not in permanent_codes:
            sent = bot.reply_to(message, "⚠️ سیستم در حال حاضر مشغول است. لطفا کمی صبر کنید.")
            delete_command_messages(message.chat.id, message.message_id, sent.message_id)
            return

        code = message.text
        sent_message = bot.reply_to(message, "🔄 کد شما در حال اجراست...", parse_mode='Markdown')

        thread = threading.Thread(
            target=execute_with_timeout,
            args=(code, sent_message.message_id, message.chat.id, message)
        )
        running_codes[sent_message.message_id] = thread
        thread.daemon = True
        thread.start()

        timer = threading.Timer(
            CODE_TIMEOUT,
            lambda: stop_code(sent_message.message_id, message.chat.id)
        )
        timer.start()

        del user_coding_state[message.reply_to_message.message_id]


def stop_code(message_id, chat_id):
    if message_id in running_codes:
        del running_codes[message_id]
        sent_message = bot.send_message(
            chat_id,
            f"⏱ کد با شناسه {message_id} به دلیل اتمام زمان متوقف شد."
        )
        threading.Timer(
            DELETE_TIMEOUT,
            lambda: bot.delete_message(chat_id, sent_message.message_id)
        ).start()


@bot.message_handler(commands=['sto'])
def ss(message):
    main1.test(bot, message)


# Set bot commands
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
logger.info("Starting bot...")
bot.remove_webhook()
bot.polling()