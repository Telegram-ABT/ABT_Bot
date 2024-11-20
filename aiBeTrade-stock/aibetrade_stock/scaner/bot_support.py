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

# Укажите токен вашего бота
TOKEN = os.getenv('TOKEN_BOT_SCANER')
bot = telebot.TeleBot(TOKEN)

# Подключение к MongoDB
mongo_url = os.getenv('MONGO_URL_SERV')
client = MongoClient(mongo_url)
db = client["nntcapital"]
collection = db["support"]
scanerchats_collection = db["scanerchats"]
scanerdialog_collection = db["scanerdialog"]
scanercall_collection = db["scanercall"]
scanersettings_collection = db["scanersettings"]
case_share_collection = db["kogan_case_share"]
case_collection = db["kogan_case"]

# Хранит состояние выбранного раздела и текст сообщения
user_state = {}

# Проверка, запущен ли скрипт bot_scaner.py
def is_scaner_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        cmdline = proc.info['cmdline']
        if cmdline and "bot_scaner.py" in cmdline:
            return proc.info['pid']
    return None

# Проверка, запущен ли скрипт bot_assistent.py
def is_sender_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        cmdline = proc.info['cmdline']
        if cmdline and "bot_assistent.py" in cmdline:
            return proc.info['pid']
    return None

# Проверка, запущен ли скрипт bot_trade.py
def is_trade_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        cmdline = proc.info['cmdline']
        if cmdline and "bot_trade.py" in cmdline:
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
    scaner_status = "Scaner"
    sender_status = "Assistent"
    trading_status = "Trading"
    buttons = [
        types.InlineKeyboardButton(scaner_status, callback_data="scaner_status"),
        types.InlineKeyboardButton("Contact list", callback_data="2"),
        types.InlineKeyboardButton(sender_status, callback_data="sender_status"),
        types.InlineKeyboardButton(trading_status, callback_data="trading_status")
    ]
    markup.add(buttons[0], buttons[1])
    markup.add(buttons[2], buttons[3])
    return markup

# Функция для создания меню управления торговлей
def create_analytics_menu():
    markup = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton("Список акций P&L>30%", callback_data="list_shares_pnl_30"),
        types.InlineKeyboardButton("Список акций P&L>20%", callback_data="list_shares_pnl_20"),
        types.InlineKeyboardButton("Назад", callback_data="back_to_trading")
    ]
    markup.add(*buttons)
    return markup

def create_trading_control_menu():
    pid = is_trade_running()
    markup = types.InlineKeyboardMarkup(row_width=2)
    if pid:
        buttons = [
            types.InlineKeyboardButton("Остановить", callback_data="stop_trade"),
            types.InlineKeyboardButton("Перезапустить", callback_data="restart_trade")
        ]
    else:
        buttons = [types.InlineKeyboardButton("Запустить", callback_data="start_trade")]

    buttons.append(types.InlineKeyboardButton("Список акций", callback_data="list_shares"))
    buttons.append(types.InlineKeyboardButton("Set price", callback_data="set_price"))
    buttons.append(types.InlineKeyboardButton("Get status", callback_data="get_status"))
    buttons.append(types.InlineKeyboardButton("setting->new", callback_data="set_new"))
    buttons.append(types.InlineKeyboardButton("complete->new", callback_data="set_complete"))
    buttons.append(types.InlineKeyboardButton("Аналитика", callback_data="analytics"))
    buttons.append(types.InlineKeyboardButton("Назад", callback_data="back"))
    markup.add(*buttons)
    return markup

# Функция для создания меню списка акций
def create_shares_menu(call, case_name=None):
    if case_name:
        bot.send_message(call.message.chat.id, f"Список акций для {case_name}", parse_mode='HTML')
    else:
        bot.send_message(call.message.chat.id, "Список всех акций", parse_mode='HTML')
    markup = types.InlineKeyboardMarkup()
    if case_name:
        shares = case_share_collection.find({"case_name": case_name})
    else:
        shares = case_share_collection.find({})
    shares_list = [f"{share['case_name']}: {share['share']} - {share['balance_count']}" for share in shares]
    for share in shares_list:
        bot.send_message(call.message.chat.id, share, parse_mode='HTML')
    markup.add(types.InlineKeyboardButton("Назад", callback_data="back_to_trading"))
    shares_text = "Список акций сформирован"
    return shares_text, markup

def create_portfolio_buttons_list():
    markup = types.InlineKeyboardMarkup()
    active_cases = case_collection.find({"active": True})
    for case in active_cases:
        markup.add(types.InlineKeyboardButton(case['case_name'], callback_data=f"portfolio_list_{case['case_name']}"))
    markup.add(types.InlineKeyboardButton("Все портфели", callback_data="portfolio_list_all"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="back_to_trading"))
    return markup

def create_portfolio_buttons_get_status():
    markup = types.InlineKeyboardMarkup()
    active_cases = case_collection.find({"active": True})
    for case in active_cases:
        markup.add(types.InlineKeyboardButton(case['case_name'], callback_data=f"portfolio_get_status_{case['case_name']}"))
    markup.add(types.InlineKeyboardButton("Все портфели", callback_data="portfolio_get_status_all"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="back_to_trading"))
    return markup

def create_portfolio_buttons_pnl():
    markup = types.InlineKeyboardMarkup()
    active_cases = case_collection.find({"active": True})
    for case in active_cases:
        markup.add(types.InlineKeyboardButton(case['case_name'], callback_data=f"portfolio_pnl_{case['case_name']}"))
    markup.add(types.InlineKeyboardButton("Все портфели", callback_data="portfolio_pnl_all"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="back_to_trading"))
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

    button_id = call.data
    user_state[call.message.chat.id] = {"section": button_id, "message_text": ""}

    if button_id == "scaner_status":
        bot.send_message(
            call.message.chat.id,
            "Выберите действие для сканера:",
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
    elif button_id == "trading_status":
        bot.send_message(
            call.message.chat.id,
            "Выберите действие для торговли:",
            reply_markup=create_trading_control_menu()
        )
    elif button_id == "list_shares":
        bot.send_message(
            call.message.chat.id,
            "Выберите портфель:",
            reply_markup=create_portfolio_buttons_list()
        )
    elif button_id == "get_status":
        bot.send_message(
            call.message.chat.id,
            "Выберите портфель для получения статуса:",
            reply_markup=create_portfolio_buttons_get_status()
        )
    elif button_id.startswith("portfolio_list_"):
        case_name = button_id.split("_")[2]
        if case_name == "all":
            shares_text, shares_markup = create_shares_menu(call)
        else:   
            shares_text, shares_markup = create_shares_menu(call, case_name)
        chunks = textwrap.wrap(shares_text, 3000)
        for i, chunk in enumerate(chunks):
            if i == len(chunks) - 1:
                bot.send_message(call.message.chat.id, chunk, reply_markup=shares_markup)
            else:
                bot.send_message(call.message.chat.id, chunk)
    elif button_id.startswith("portfolio_get_status_"):
        case_name = button_id.split("_")[3]
        if case_name == "all":
            text_message = asyncio.run(process_get_status_message(bot, call.message.chat.id))
        else:
            text_message = asyncio.run(process_get_status_message(bot, call.message.chat.id, case_name))
        bot.send_message(call.message.chat.id, text_message, reply_markup=create_trading_control_menu())
    elif button_id == "back_to_trading":
        bot.send_message(
            call.message.chat.id,
            "Выберите действие для торговли:",
            reply_markup=create_trading_control_menu()
        )
    elif button_id == "start_scaner":
        start_script("bot_scaner.py")
        bot.send_message(
            call.message.chat.id,
            "Сканер успешно запущен.",
            reply_markup=create_main_menu()
        )
    elif button_id == "stop_scaner":
        pid = is_scaner_running()
        if pid:
            stop_script(pid)
            bot.send_message(
                call.message.chat.id,
                "Сканер успешно остановлен.",
                reply_markup=create_main_menu()
            )
        else:
            bot.send_message(
                call.message.chat.id,
                "Сканер уже остановлен.",
                reply_markup=create_main_menu()
            )
    elif button_id == "restart_scaner":
        pid = is_scaner_running()
        if pid:
            stop_script(pid)
        start_script("bot_scaner.py")
        bot.send_message(
            call.message.chat.id,
            "Сканер успешно перезапущен.",
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
    elif button_id == "start_trade":
        start_script("bot_trade.py")
        bot.send_message(
            call.message.chat.id,
            "Торговля успешно заущена.",
            reply_markup=create_main_menu()
        )
    elif button_id == "stop_trade":
        pid = is_trade_running()
        if pid:
            stop_script(pid)
            bot.send_message(
                call.message.chat.id,
                "Торговля успешно остановлена.",
                reply_markup=create_main_menu()
            )
        else:
            bot.send_message(
                call.message.chat.id,
                "Торговля уже остановлена.",
                reply_markup=create_main_menu()
            )
    elif button_id == "restart_trade":
        pid = is_trade_running()
        if pid:
            stop_script(pid)
        start_script("bot_trade.py")
        bot.send_message(
            call.message.chat.id,
            "Торговля успешно перезапущена.",
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
            "Найенные каналы. Выберите для какого канала сформировать базу для рассылки сообщений",
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
    elif button_id == "set_price":
        bot.send_message(call.message.chat.id, "Процедура установки цена для акций запущена.", reply_markup=create_trading_control_menu())
        asyncio.run(process_set_price_message())
    elif button_id == "set_new":
        asyncio.run(process_set_new_message())
        bot.send_message(call.message.chat.id, "Статус сигналов обновлен с 'setting' на 'new'.", reply_markup=create_trading_control_menu())
    elif button_id == "set_complete":
        asyncio.run(process_set_complete_message())
        bot.send_message(call.message.chat.id, "Статус сигналов обновлен с 'complete' на 'new'.", reply_markup=create_trading_control_menu())
    elif button_id == "get_status":
        text_message = asyncio.run(process_get_status_message(bot,call.message.chat.id))
        bot.send_message(call.message.chat.id, text_message, reply_markup=create_trading_control_menu())
    elif button_id == "analytics":
        bot.send_message(call.message.chat.id, "Аналитика", reply_markup=create_analytics_menu())
    elif button_id == "list_shares_pnl_30":
        bot.send_message(
            call.message.chat.id,
            "Выберите портфель для P&L>30%:",
            reply_markup=create_portfolio_buttons_pnl()
        )
    elif button_id == "list_shares_pnl_20":
        bot.send_message(
            call.message.chat.id,
            "Выберите портфель для P&L>20%:",
            reply_markup=create_portfolio_buttons_pnl()
        )
    elif button_id.startswith("portfolio_pnl_30"):
        case_name = button_id.split("_")[3]
        if case_name == "all":
            message = process_pnl_selection(30)
        else:
            message = process_pnl_selection(30, case_name)
        bot.send_message(call.message.chat.id, message)
    elif button_id.startswith("portfolio_pnl_20"):
        case_name = button_id.split("_")[3]
        if case_name == "all":
            message = process_pnl_selection(20)
        else:
            message = process_pnl_selection(20, case_name)
        bot.send_message(call.message.chat.id, message)

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

    # Определям количество записей в результате
    num_records = len(results)
    print(f"Количество записей в результате агрегации: {num_records}")

    if num_records > 0:
        # Если записей больше 0, запрашиваем промт для ChatGPT
        bot.send_message(
            chat_id,
            "Пришлите ПРОМТ для chatGPT, чтобы оптимально вступить и поддерживать диалог с пользователями."
        )
        user_state[chat_id]["awaiting_promt"] = selected_chat_id

    for result in results:
        scanercall_collection.insert_one({
            "user_id": result["user_id"],
            "texts_message": " ".join(result["texts_message"]),
            "chat_name": chat_name,
            "id_chat": selected_chat_id,
            "firstcall": False
        })

    bot.send_message(
        chat_id,
        f"База для рассылки сообщений подготовлена, всего записей: {num_records}",
        reply_markup=create_main_menu()
    )

# Обработка текстовых сообщений от пользователя
@bot.message_handler(func=lambda message: True)
def handle_text_input(message):
    user_id = message.chat.id
    state = user_state.get(user_id)

    if state and state.get("awaiting_promt"):
        # Получаем id_chat и promt от пользователя
        id_chat = state["awaiting_promt"]
        promt = message.text

        # Сохраняем или обновляем promt в scanersettings
        scanersettings_collection.update_one(
            {"id_chat": id_chat},
            {"$set": {"promt": promt}},
            upsert=True
        )

        # Запрашиваем описание чата или канала
        bot.send_message(user_id, "Введите описание чата или канала.")
        user_state[user_id]["awaiting_chat_discr"] = id_chat
        user_state[user_id]["awaiting_promt"] = None  # Сбрасываем состояние ожидания промта

    elif state and state.get("awaiting_chat_discr"):
        # Получаем id_chat и описание чата от пользователя
        id_chat = state["awaiting_chat_discr"]
        chat_discr = message.text

        # Сохраняем или обновляем chat_discr в scanersettings
        scanersettings_collection.update_one(
            {"id_chat": id_chat},
            {"$set": {"chat_discr": chat_discr}},
            upsert=True
        )

        # Подтверждаем сохранение описания и сбрасываем состояние
        bot.send_message(user_id, "Описание чата или канала успешно сохранено.", reply_markup=create_main_menu())
        user_state[user_id]["awaiting_chat_discr"] = None

# Функция для очистки таблицы scanercall
def clear_scanercall(chat_id):
    scanercall_collection.delete_many({})
    bot.send_message(
        chat_id,
        "Удаление данных прошло успешно",
        reply_markup=create_main_menu()
    )

def create_data_collection_menu():
    markup = types.InlineKeyboardMarkup()
    # Добавьте кнопки и логику для меню
    markup.add(types.InlineKeyboardButton("Назад", callback_data="back"))
    return markup
# Запуск бота
bot.polling(none_stop=True)
