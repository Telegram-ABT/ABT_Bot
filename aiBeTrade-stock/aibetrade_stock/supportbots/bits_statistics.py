from pymongo import MongoClient
import os
from datetime import datetime

def get_statistics():
    try:
        # Подключение к MongoDB
        mongo_client = MongoClient(os.getenv('MONGO_URL_SERV'))
        db = mongo_client["nntcapital"]
        collection = db["bits_data_trade"]
        strategy_id = "roman_strat"
        
        # Получаем последнюю запись, сортируя по полю date в обратном порядке
        last_record = collection.find_one(
            {"strategy_id": strategy_id},  # пустой фильтр для выбора всех документов
            sort=[("date", -1)]  # сортировка по date в обратном порядке
        )
        
        if last_record:
            # Преобразуем ObjectId в строку для возможности сериализации
            last_record['_id'] = str(last_record['_id'])
            return last_record
        else:
            return {"error": "Записи не найдены"}
            
    except Exception as e:
        return {"error": f"Ошибка при получении статистики: {str(e)}"}
    finally:
        mongo_client.close()

# Функция для публикации в Telegram
def publish_to_telegram(combo_text_ru, combo_text_en):
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
