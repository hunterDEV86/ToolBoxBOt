import telebot


def test(bot, message):
    bot.send_message(message.chat.id, "Hello, World!")
