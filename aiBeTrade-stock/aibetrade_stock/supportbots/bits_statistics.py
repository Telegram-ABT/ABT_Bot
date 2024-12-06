from pymongo import MongoClient
import os
from datetime import datetime
import telebot
import logging

logger = logging.getLogger('BitsBot')

def get_statistics(bot,chat_id,lang):
    try:
        # Подключение к MongoDB
        user_lang = lang
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
            send_bot = publish_to_telegram(last_record['_id']) 
            return send_bot
        else:
            return {"error": "Записи не найдены"}
            
    except Exception as e:
        return {"error": f"Ошибка при получении статистики: {str(e)}"}
    finally:
        mongo_client.close()

# Функция для публикации в Telegram
def publish_to_telegram(bot, chat_id, stst_data):
        image_path = stst_data['image_path']
        days = stst_data['days']
        is_successful = stst_data['is_successful']
        profit = stst_data['profit']
        totalProfit = stst_data['totalProfit']
        strategy_name = stst_data['strategy_name']
        if is_successful:
            image_path = image_path
            message_text = (
                f"🟢 <b>ABT Bits Pro: day trading was Successful!</b>\n\n"
                f"Strategy: <b>{strategy_name}</b>\n"
                f"Profit of trade is: <b>{profit}%</b>\n"
                f"Total profit: <b>{totalProfit}%</b>\n"
                f"Number of Trading Days: <b>{days}</b>"
            )
        else:
            image_path = "pic/failure.jpg"
            message_text = (
                f"🔴 <b>ABT Bits Pro: day trading was Failure!</b>\n\n"
                f"Strategy: <b>{strategy_name}</b>\n"
                f"Profit of trade is: <b>{profit}%</b>\n"
                f"Total profit: <b>{totalProfit}%</b>\n"
                f"Number of Trading Days: <b>{days}</b>"
            )



        # Публикация английского поста с картинкой
        button1_en = telebot.types.InlineKeyboardButton("🚀 ABT Bits Pro chanel", url="https://t.me/abtbits")
        button2_en = telebot.types.InlineKeyboardButton("💼 ABT Bits Pro news", url="https://forms.gle/abtbitxx")


        # Добавление кнопок в одну строку
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(button1_en)
        markup.add(button2_en)

        with open(image_path, 'rb') as photo:
            bot.send_photo(chat_id, photo, caption=message_text, reply_markup=markup, parse_mode='HTML')

        logger.info("Сообщения успешно опубликованы в Telegram.")
