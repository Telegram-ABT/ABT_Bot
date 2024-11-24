import telebot
from telebot import types
from datetime import datetime
from pymongo import MongoClient
import psutil
import subprocess
import os
import signal
import asyncio
from bot_signal import process_set_new_message, process_set_complete_message, process_set_price_message
from bot_trade import process_get_status_message
import textwrap
import time
from analits import process_pnl_selection

mongo_url = os.getenv('MONGO_URL_SERV')
client = MongoClient(mongo_url)
db = client["nntcapital"]
info_settings = db['bot_secrtary_settings']

# Укажите токен вашего бота
key_bot_record = info_settings.find({})
if key_bot_record is None:
    raise ValueError("Запись с ключом 'bot_key' не найдена в коллекции 'bot_secrtary_settings'.")
key_bot = None
for record in key_bot_record:
    key_bot = record.get('allknowsbro_bot')
if not key_bot:
    raise ValueError("Пожалуйста, установите переменные окружения: allknowsbro_bot")

TELEGRAM_BOT_TOKEN = key_bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Подключение к MongoDB

# Хранит состояние выбранного раздела и текст сообщения
user_state = {}

# Разрешенный пользователь

# Проверка, запущен ли скрипт bot_scaner.py
# Проверка, запущен ли скрипт secretary.py
def is_secretary_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        cmdline = proc.info['cmdline']
        if cmdline and "secretary.py" in cmdline:
            return proc.info['pid']
    return None

# Проверка, запущен ли скрипт bot_assistent.py
# Функция для запуска скриптов
def start_secretary(script_name):
    return subprocess.Popen(["python3", script_name])

# Функция для остановки скриптов
def stop_secretary(pid):
    os.kill(pid, signal.SIGTERM)


# Функция для создания inline-кнопок главного меню
def create_main_menu():
    markup = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton("Secretary", callback_data="secretary_status")
    ]
    markup.add(buttons[0])
    return markup


# Обработка команды /start и /menu
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "Привет! Давай запустим бот:",
        reply_markup=create_main_menu()
    )
    user_state[message.chat.id] = {"section": None, "message_text": ""}

# Обработка нжатия inline-кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

    button_id = call.data
    user_state[call.message.chat.id] = {"section": button_id, "message_text": ""}

    if button_id == "secretary_status":
            bot.send_message(
            call.message.chat.id,
            "<b>Приветствуем вас в боте секретарь!</b>\n\n"
            "Что умеет этот бот:\n\n"
            "Секретарь отвечает на вопросы пользователя на базе базы знаний.\n\n"
            "Выберите действие для секретаря:",
            reply_markup=create_secretary_control_menu(), parse_mode='HTML'
        )
    elif button_id == "start_secretary":
        start_secretary("secretary.py")
        bot.send_message(
            call.message.chat.id,
            "Секретарь успешно запущен.",
            reply_markup=create_main_menu()
        )
    elif button_id == "stop_secretary":
        pid = is_secretary_running()
        if pid:
            stop_secretary(pid)
            bot.send_message(
                call.message.chat.id,
                "Секретарь успешно остановлен.",
                reply_markup=create_main_menu()
            )
    elif button_id == "restart_secretary":
        pid = is_secretary_running()
        if pid:
            stop_secretary(pid)
        start_secretary("secretary.py")
        bot.send_message(
            call.message.chat.id,
            "Секретарь успешно перезапущен.",
            reply_markup=create_main_menu()
        )
    elif button_id == "back":
        bot.send_message(
            call.message.chat.id,
            "Выберите одну из опций:",
            reply_markup=create_main_menu()
        )
        user_state[call.message.chat.id] = {"section": None, "message_text": ""}

# Обработка текстовых сообщений от пользователя
def create_secretary_control_menu():
    pid = is_secretary_running()
    markup = types.InlineKeyboardMarkup(row_width=2)
    if pid:
        buttons = [
            types.InlineKeyboardButton("Остановить", callback_data="stop_secretary"),
            types.InlineKeyboardButton("Перезапустить", callback_data="restart_secretary")
        ]
    else:
        buttons = [types.InlineKeyboardButton("Запустить секретаря", callback_data="start_secretary")]
    buttons.append(types.InlineKeyboardButton("Назад", callback_data="back"))
    markup.add(*buttons)
    return markup

# Запуск бота
bot.polling(none_stop=True)
