import telebot
from telebot import types
from datetime import datetime
from pymongo import MongoClient
import psutil
import subprocess
import os
import signal
from telethon import TelegramClient, events

# Укажите токен вашего бота
TOKEN = os.getenv('TOKEN_BOT_SCANER')
bot = telebot.TeleBot(TOKEN)

# Настройки для клиента Telethon
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
USER_PHONE = os.getenv('USER_PHONE')

# Инициализация клиента Telethon
telethon_client = TelegramClient('user_session', API_ID, API_HASH, system_version="4.16.32-vxCUSTOM", device_model='FastAPI Galaxy S24 Ultra, running Android 14')

# Подключение к MongoDB
mongo_url = os.getenv('MONGO_URL')
mongo_client = MongoClient(mongo_url)
db = mongo_client["nntcapital"]
collection = db["support"]
scanerchats_collection = db["scanerchats"]
scanerdialog_collection = db["scanerdialog"]
scanercall_collection = db["scanercall"]
scanersettings_collection = db["scanersettings"]

# Хранит состояние выбранного раздела и текст сообщения
user_state = {}

# Функция для отправки сообщения через Telegram
async def send_telegram_message(user_id, message_text):
    try:
        user_entity = await telethon_client.get_entity(user_id)
        await telethon_client.send_message(user_entity, message_text)
        print(f"Сообщение отправлено пользователю {user_id}: {message_text}")
    except Exception as e:
        print(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

# Обработчик входящих сообщений
@telethon_client.on(events.NewMessage)
async def handle_incoming_message(event):
    user_id = event.sender_id
    user_message = event.raw_text
    print(f"Получено новое сообщение от пользователя {user_id}: {user_message}")

    # Здесь можно добавить логику для обработки сообщений
    # Например, передать сообщение в bot_scaner или bot_sender для обработки

# Запуск клиента Telethon при старте скрипта
telethon_client.start(phone=USER_PHONE)

# Запуск бота
bot.polling(none_stop=True)
