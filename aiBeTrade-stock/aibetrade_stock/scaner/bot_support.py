import telebot
from telebot import types
from datetime import datetime
from pymongo import MongoClient
import psutil
import subprocess
import os
import signal

# Укажите токен вашего бота
TOKEN = os.getenv('TOKEN_BOT_SCANER')
bot = telebot.TeleBot(TOKEN)

# Подключение к MongoDB
mongo_url = os.getenv('MONGO_URL_SERV')  # Замените на URL MongoDB сервера
client = MongoClient(mongo_url)
db = client["nntcapital"]
collection = db["support"]
scanerchats_collection = db["scanerchats"]
scanerdialog_collection = db["scanerdialog"]
scanercall_collection = db["scanercall"]
scanersettings_collection = db["scanersettings"]

# Хранит состояние выбранного раздела и текст сообщения
user_state = {}

# Проверка, запущен ли скрипт bot_scaner.py
def is_scaner_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        cmdline = proc.info['cmdline']
        if cmdline and "bot_assistent.py" in cmdline:  # Изменено на bot_assistent.py
            return proc.info['pid']
    return None

# Проверка, запущен ли скрипт bot_assistent.py
def is_sender_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        cmdline = proc.info['cmdline']
        if cmdline and "bot_assistent.py" in cmdline:
            return proc.info['pid']
    return None

# Функция для запуска скриптов
def start_script(script_name):
    return subprocess.Popen(["python3", script_name])

# Функция для остановки скриптов
def stop_script(pid):
    os.kill(pid, signal.SIGTERM)

# Функция для создания inline-кнопок главного меню
def create_main_menu():
    markup = types.InlineKeyboardMarkup()
    scaner_status = "Multi Agent"  # Изменено название кнопки
    sender_status = "Assistent" 
    buttons = [
        types.InlineKeyboardButton(scaner_status, callback_data="scaner_status"),
        types.InlineKeyboardButton("Contact list", callback_data="2"),
        types.InlineKeyboardButton(sender_status, callback_data="sender_status"),
        types.InlineKeyboardButton("Settings", callback_data="4")
    ]
    markup.add(buttons[0], buttons[1])
    markup.add(buttons[2], buttons[3])
    return markup

# Функция для создания меню управления сканером
def create_scaner_control_menu():
    pid = is_scaner_running()
    markup = types.InlineKeyboardMarkup(row_width=2)
    if pid:
        buttons = [
            types.InlineKeyboardButton("Остановить", callback_data="stop_scaner"),
            types.InlineKeyboardButton("Перезапустить", callback_data="restart_scaner")
        ]
    else:
        buttons = [types.InlineKeyboardButton("Запустить сканер", callback_data="start_scaner")]
    buttons.append(types.InlineKeyboardButton("Назад", callback_data="back"))
    markup.add(*buttons)
    return markup

# Функция для создания меню управления рассылкой
def create_sender_control_menu():
    pid = is_sender_running()
    markup = types.InlineKeyboardMarkup(row_width=2)
    if pid:
        buttons = [
            types.InlineKeyboardButton("Остановить", callback_data="stop_sender"),
            types.InlineKeyboardButton("Перезапустить", callback_data="restart_sender")
        ]
    else:
        buttons = [types.InlineKeyboardButton("Запустить", callback_data="start_sender")]
    buttons.append(types.InlineKeyboardButton("Назад", callback_data="back"))
    markup.add(*buttons)
    return markup

# Функция для создания меню сбора базы данных рассылки
def create_data_collection_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("Сформировать БД", callback_data="2.1"),
        types.InlineKeyboardButton("Очистить БД", callback_data="2.2")
    ]
    buttons.append(types.InlineKeyboardButton("Назад", callback_data="back"))
    markup.add(*buttons)
    return markup

# Функция для создания кнопок каналов из базы данных
def create_channel_buttons():
    markup = types.InlineKeyboardMarkup()
    channels = scanerchats_collection.find({}, {"chat_id": 1, "chat_name": 1})
    for channel in channels:
        button_text = f"{channel['chat_name']} (ID: {channel['chat_id']})"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"channel_{channel['chat_id']}"))
    print(f"Сгенерированы кнопки для каналов: {[button_text for channel in channels]}")
    return markup

# Функция для создания кнопок выбора действия (Изменить/Оставить)
def create_edit_buttons(action_type):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("Изменить", callback_data=f"edit_{action_type}"),
        types.InlineKeyboardButton("Оставить", callback_data=f"keep_{action_type}")
    ]
    markup.add(*buttons)
    return markup

# Обработка команды /start и /menu
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "Привет! Выберите одну из опций:",
        reply_markup=create_main_menu()
    )
    user_state[message.chat.id] = {"section": None, "message_text": ""}

# Обработка нажатия inline-кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

    user_id = call.from_user.id
    button_id = call.data
    user_state[call.message.chat.id] = {"section": button_id, "message_text": ""}

    if button_id == "scaner_status":
        bot.send_message(
            call.message.chat.id,
            "Выберите действие для Multi Agent:",  # Изменен текст сообщения
            reply_markup=create_scaner_control_menu()
        )
    elif button_id == "sender_status":
        if is_scaner_running():
            bot.send_message(
                call.message.chat.id,
                "Запущен сканер, запуск Рассылки невозможен",
                reply_markup=create_main_menu()
            )
        else:
            bot.send_message(
                call.message.chat.id,
                "Выберите действие для рассылки:",
                reply_markup=create_sender_control_menu()
            )
    elif button_id == "start_scaner":
        start_script("bot_assistent.py")  # Изменено на bot_assistent.py
        bot.send_message(
            call.message.chat.id,
            "Multi Agent успешно запущен.",  # Изменен текст сообщения
            reply_markup=create_main_menu()
        )
    elif button_id == "stop_scaner":
        pid = is_scaner_running()
        if pid:
            stop_script(pid)
            bot.send_message(
                call.message.chat.id,
                "Multi Agent успешно остановлен.",  # Изменен текст сообщения
                reply_markup=create_main_menu()
            )
        else:
            bot.send_message(
                call.message.chat.id,
                "Multi Agent уже остановлен.",  # Изменен текст сообщения
                reply_markup=create_main_menu()
            )
    elif button_id == "restart_scaner":
        pid = is_scaner_running()
        if pid:
            stop_script(pid)
        start_script("bot_assistent.py")  # Изменено на bot_assistent.py
        bot.send_message(
            call.message.chat.id,
            "Multi Agent успешно перезапущен.",  # Изменен текст сообщения
            reply_markup=create_main_menu()
        )
    elif button_id == "start_sender":
        start_script("bot_assistent.py")
        bot.send_message(
            call.message.chat.id,
            "Сервис успешно запущен.",
            reply_markup=create_main_menu()
        )
    elif button_id == "stop_sender":
        pid = is_sender_running()
        if pid:
            stop_script(pid)
            bot.send_message(
                call.message.chat.id,
                "Сервис успешно остановлен.",
                reply_markup=create_main_menu()
            )
        else:
            bot.send_message(
                call.message.chat.id,
                "Сервис уже остановлен.",
                reply_markup=create_main_menu()
            )
    elif button_id == "restart_sender":
        pid = is_sender_running()
        if pid:
            stop_script(pid)
        start_script("bot_assistent.py")
        bot.send_message(
            call.message.chat.id,
            "Сервис успешно перезапущен.",
            reply_markup=create_main_menu()
        )
    elif button_id == "2":
        bot.send_message(
            call.message.chat.id,
            "Выберите действие:",
            reply_markup=create_data_collection_menu()
        )
    elif button_id == "2.1":
        bot.send_message(
            call.message.chat.id,
            "Найденные каналы. Выберите для какого канала сформировать базу для рассылки сообщений",
            reply_markup=create_channel_buttons()
        )
    elif button_id.startswith("channel_"):
        chat_id = int(button_id.split("_")[1])
        handle_database_formation(call.message.chat.id, chat_id)
    elif button_id == "2.2":
        clear_scanercall(call.message.chat.id)
    elif button_id == "back":
        bot.send_message(
            call.message.chat.id,
            "Выберите одну из опций:",
            reply_markup=create_main_menu()
        )
        user_state[call.message.chat.id] = {"section": None, "message_text": ""}

# Функция для формирования базы данных
def handle_database_formation(chat_id, selected_chat_id):
    chat_info = scanerchats_collection.find_one({"chat_id": selected_chat_id}, {"chat_name": 1})
    chat_name = chat_info.get("chat_name", "Неизвестный чат") if chat_info else "Неизвестный чат"

    pipeline = [
        {"$match": {"id_chat": selected_chat_id}},
        {"$sort": {"date": -1}},
        {"$group": {
            "_id": "$id_user",
            "texts_message": {"$push": "$message"}
        }},
        {"$project": {
            "user_id": "$_id",
            "texts_message": {"$slice": ["$texts_message", 10]}
        }}
    ]
    results = list(scanerdialog_collection.aggregate(pipeline))

    for result in results:
        scanercall_collection.insert_one({
            "user_id": result["user_id"],
            "texts_message": " ".join(result["texts_message"]),
            "chat_name": chat_name,
            "id_chat": selected_chat_id,
            "firstcall": False
        })

    count = scanercall_collection.count_documents({})
    bot.send_message(
        chat_id,
        f"База для рассылки сообщений подготовлена, всего записей: {count}",
        reply_markup=create_main_menu()
    )

    if count > 0:
        # Проверяем существующие настройки
        settings = scanersettings_collection.find_one({"id_chat": selected_chat_id})
        if settings and settings.get("promt"):
            # Если промт уже существует
            bot.send_message(
                chat_id,
                f"Промт уже заполнен: {settings['promt']}",
                reply_markup=create_edit_buttons("promt")
            )
            user_state[chat_id] = {
                "awaiting_promt": selected_chat_id,
                "existing_settings": settings
            }
        else:
            # Если промта нет
            bot.send_message(
                chat_id,
                "Пришлите ПРОМТ для chatGPT, чтобы оптимально вступить и поддерживать диалог с пользователями."
            )
            user_state[chat_id] = {"awaiting_promt": selected_chat_id}

# Обработка нажатий на кнопки Изменить/Оставить
@bot.callback_query_handler(func=lambda call: call.data.startswith(('edit_', 'keep_')))
def handle_edit_keep_choice(call):
    user_id = call.message.chat.id
    action, field = call.data.split('_')
    state = user_state.get(user_id, {})
    
    if field == "promt":
        if action == "edit":
            bot.edit_message_text(
                "Введите новый Промт в строку сообщения и отправьте",
                user_id,
                call.message.message_id
            )
            state["awaiting_new_promt"] = True
        else:  # keep
            # Переходим к проверке описания чата
            settings = state.get("existing_settings", {})
            if settings.get("chat_discr"):
                bot.edit_message_text(
                    f"Описание группы уже заполнено: {settings['chat_discr']}",
                    user_id,
                    call.message.message_id,
                    reply_markup=create_edit_buttons("descr")
                )
            else:
                bot.edit_message_text(
                    "Введите описание чата или канала.",
                    user_id,
                    call.message.message_id
                )
                state["awaiting_chat_discr"] = state["awaiting_promt"]
                state["awaiting_promt"] = None
    
    elif field == "descr":
        if action == "edit":
            bot.edit_message_text(
                "Введите новое Описание группы в строку сообщения и отправьте",
                user_id,
                call.message.message_id
            )
            state["awaiting_new_descr"] = True
        else:  # keep
            # Завершаем процесс
            bot.delete_message(user_id, call.message.message_id)
            bot.send_message(
                user_id,
                "Настройки сохранены",
                reply_markup=create_main_menu()
            )
            state.clear()
    
    user_state[user_id] = state

# Обработка текстовых сообщений от пользователя
@bot.message_handler(func=lambda message: True)
def handle_text_input(message):
    user_id = message.chat.id
    state = user_state.get(user_id, {})

    if state.get("awaiting_promt") or state.get("awaiting_new_promt"):
        id_chat = state["awaiting_promt"]
        promt = message.text

        # Сохраняем или обновляем promt в scanersettings
        scanersettings_collection.update_one(
            {"id_chat": id_chat},
            {"$set": {"promt": promt}},
            upsert=True
        )

        # Проверяем существующее описание чата
        settings = scanersettings_collection.find_one({"id_chat": id_chat})
        if settings and settings.get("chat_discr") and not state.get("awaiting_new_promt"):
            bot.send_message(
                user_id,
                f"Описание группы уже заполнено: {settings['chat_discr']}",
                reply_markup=create_edit_buttons("descr")
            )
        else:
            bot.send_message(user_id, "Введите описание чата или канала.")
            state["awaiting_chat_discr"] = id_chat

        state["awaiting_promt"] = None
        state["awaiting_new_promt"] = None
        user_state[user_id] = state

    elif state.get("awaiting_chat_discr") or state.get("awaiting_new_descr"):
        id_chat = state.get("awaiting_chat_discr") or state["awaiting_promt"]
        chat_discr = message.text

        # Сохраняем или обновляем chat_discr в scanersettings
        scanersettings_collection.update_one(
            {"id_chat": id_chat},
            {"$set": {"chat_discr": chat_discr}},
            upsert=True
        )

        # Завершаем процесс
        bot.send_message(
            user_id,
            "Настройки успешно сохранены",
            reply_markup=create_main_menu()
        )
        user_state[user_id].clear()

# Функция для очистки таблицы scanercall
def clear_scanercall(chat_id):
    scanercall_collection.delete_many({})
    bot.send_message(
        chat_id,
        "Удаление данных прошло успешно",
        reply_markup=create_main_menu()
    )

# Запуск бота
bot.polling(none_stop=True)
