import time
import os
import random
import logging
from datetime import datetime, timedelta
from pymongo import MongoClient
import telebot

# Инициализация логгера
logging.basicConfig(
    filename='combo_publisher.log',  # Лог-файл
    filemode='a',  # Режим записи (a - добавление новых записей)
    format='%(asctime)s - %(levelname)s - %(message)s',  # Формат логирования
    level=logging.INFO  # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
)

logger = logging.getLogger()

# Подключение к MongoDB через параметры окружения
mongo_url = os.getenv('MONGO_URL')  # Замените на URL MongoDB сервера
db_name = 'aibetrade'  # Название базы данных
collection_name = 'combo'  # Название коллекции

# Инициализация MongoDB
client = MongoClient(mongo_url)

# Инициализация бота Telegram через переменные окружения
telegram_token = os.getenv('API_BOT_CR')  # Замените на ваш Telegram Bot API token
chat_id_ru = '-1001609461642'  # Замените на ID чата для русского поста
chat_id_en = '-1001967803227'  # Замените на ID чата для английского поста

bot = telebot.TeleBot(telegram_token)

# Пути к изображениям
image_path_ru = 'pic/combo_rus.jpg'
image_path_en = 'pic/combo_eng.jpg'

# Функция для проверки наличия базы данных и коллекции
def check_db_and_collection():
    # Проверяем наличие базы данных
    db_list = client.list_database_names()
    if db_name in db_list:
        logger.info(f"База данных '{db_name}' существует.")
        db = client[db_name]
        # Проверяем наличие коллекции
        if collection_name in db.list_collection_names():
            logger.info(f"Коллекция '{collection_name}' существует.")
            return True
        else:
            logger.warning(f"Коллекция '{collection_name}' не существует.")
            return False
    else:
        logger.warning(f"База данных '{db_name}' не существует.")
        return False

# Функция для публикации в Telegram
def publish_to_telegram(combo_text_ru, combo_text_en):
    try:
        # Публикация русского поста с картинкой
        markup_ru = telebot.types.InlineKeyboardMarkup()
        button1_ru = telebot.types.InlineKeyboardButton("🚀 Go to ABT Miner", url="https://t.me/aibetradecombot")
        button2_ru = telebot.types.InlineKeyboardButton("💼 Амбассадорство", url="https://forms.gle/CuJJGWReWM8STR1S7")
        button1 = telebot.types.InlineKeyboardButton("🎉", callback_data='celebrate')
        button2 = telebot.types.InlineKeyboardButton("🔥", callback_data='fire')
        button3 = telebot.types.InlineKeyboardButton("😎", callback_data='cool')
        button4 = telebot.types.InlineKeyboardButton("😍", callback_data='love')
        button5 = telebot.types.InlineKeyboardButton("🤩", callback_data='star')

        # Добавление кнопок в одну строку
        markup_ru.add(button1, button2, button3, button4, button5)
        markup_ru.add(button1_ru)
        markup_ru.add(button2_ru)


        with open(image_path_ru, 'rb') as photo_ru:
            bot.send_photo(chat_id_ru, photo_ru, caption=combo_text_ru, reply_markup=markup_ru, parse_mode='HTML')

        # Публикация английского поста с картинкой
        markup_en = telebot.types.InlineKeyboardMarkup()
        button1_en = telebot.types.InlineKeyboardButton("🚀 Go to ABT Miner", url="https://t.me/aibetradecombot")
        button2_en = telebot.types.InlineKeyboardButton("💼 Be Ambassador", url="https://forms.gle/2P3GwRaMWt1Q381A6")


        button1 = telebot.types.InlineKeyboardButton("🎉", callback_data='celebrate')
        button2 = telebot.types.InlineKeyboardButton("🔥", callback_data='fire')
        button3 = telebot.types.InlineKeyboardButton("😎", callback_data='cool')
        button4 = telebot.types.InlineKeyboardButton("😍", callback_data='love')
        button5 = telebot.types.InlineKeyboardButton("🤩", callback_data='star')

        # Добавление кнопок в одну строку
        markup_en.add(button1, button2, button3, button4, button5)
        markup_en.add(button1_en)
        markup_en.add(button2_en)

        with open(image_path_en, 'rb') as photo_en:
            bot.send_photo(chat_id_en, photo_en, caption=combo_text_en, reply_markup=markup_en, parse_mode='HTML')

        logger.info("Сообщения успешно опубликованы в Telegram.")
    except Exception as e:
        logger.error(f"Ошибка при публикации в Telegram: {e}")

# Функция для генерации секретного кода
def generate_combo_data():
    # Шаг 1: Генерация случайной последовательности из 8 положений
    positions = ["left", "right", "down", "up"]
    combo = ",".join(random.choices(positions, k=8))

    # Шаг 2: Заменяем направления на эмодзи и одно случайное положение на ❓
    emoji_mapping = {
        "left": "⬅️",
        "right": "➡️",
        "down": "⬇️",
        "up": "⬆️"
    }

    combo_list = combo.split(",")
    random_index = random.randint(0, 7)  # Случайное положение для замены на ❓
    combodays_list = [emoji_mapping.get(pos, pos) for pos in combo_list]
    combodays_list[random_index] = "❓"
    combodays = "".join(combodays_list)  # Убираем запятые и пробелы

    # Шаг 3: Генерация сообщений на русском и английском
    combo_text_ru = f"<b>Всем</b> 👋\n\nУтренний секретный код уже активирован!\n\n{combodays}\n\n<b>Отличного дня!</b> 😎"
    combo_text_en = f"<b>Hello everyone</b> 👋\n\nThe morning secret code is now activated!\n\n{combodays}\n\n<b>Have a great day!</b> 😎"

    # Шаг 4: Формирование данных для записи в MongoDB
    now = datetime.now()
    date_str = now.strftime('%Y%m%d')  # Форматируем год, месяц и день
    uid = f"SUMMERCOMBO{date_str}"
    name = f"Mega Lega Combo {date_str}"

    # Генерация случайного числа для поля amount
    random_amount = random.randint(5, 500) * 1000000000

    # Даты начала и конца
    start_at = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_at = start_at + timedelta(days=2, seconds=-1)

    # Структура данных для записи
    data = {
        "uid": uid,
        "name": name,
        "code": combo,
        "currencyCode": "abt",
        "precision": 9,
        "amount": int(random_amount),
        "priseCode": "",
        "limit": 5000000,
        "count": 0,
        "startAt": start_at,
        "endAt": end_at,
        "isActive": True
    }

    return data, combo_text_ru, combo_text_en

# Функция для попытки записи в MongoDB с перегенерацией данных в случае неудачи
def attempt_to_save_data():
    while True:
        try:
            # Генерация данных
            data, combo_text_ru, combo_text_en = generate_combo_data()

            # Попытка записи данных в MongoDB
            collection = client[db_name][collection_name]  # Используем правильную коллекцию
            collection.insert_one(data)
            logger.info(f"Данные успешно записаны в MongoDB: {data}")
            
            # После успешной записи публикуем в Telegram
            publish_to_telegram(combo_text_ru, combo_text_en)
            break  # Прерываем цикл, если запись успешна

        except Exception as e:
            # В случае неудачи выводим сообщение об ошибке и перегенерируем данные
            logger.error(f"Ошибка при записи в MongoDB: {e}. Перегенерация данных...")

def run_at_9am():
    if check_db_and_collection():  # Проверяем наличие базы данных и коллекции
        while True:
            now = datetime.now()
            target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)

            # Если текущее время уже прошло 9:00 сегодня, ждём до 9:00 следующего дня
            if now > target_time:
                target_time += timedelta(days=1)

            # Вычисляем, сколько секунд до 9 утра
            time_to_wait = (target_time - now).total_seconds()
            logger.info(f"Ожидание до 9 утра: {time_to_wait // 3600} часов, {time_to_wait % 3600 // 60} минут")
            
            # Ждем до 9 утра
            time.sleep(time_to_wait)

            # Запускаем попытку записи данных в MongoDB и публикации в Telegram
            attempt_to_save_data()

    else:
        logger.error("Ошибка: Убедитесь, что база данных и коллекция существуют.")

# Функция, которая запускается один раз при старте
def run_once():
    # Проверяем наличие базы данных и коллекции
    if check_db_and_collection():
        now = datetime.now()
        target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)

        # Проверяем, совпадает ли текущее время с 9:00 утра
        logger.info("Запускаем процесс...")
            
        # Запускаем попытку записи данных в MongoDB и публикации в Telegram
        attempt_to_save_data()
    else:
        logger.error("Ошибка: Убедитесь, что база данных и коллекция существуют.")

# Запуск выполнения один раз при старте
if __name__ == "__main__":
    # run_once()
    run_at_9am()
