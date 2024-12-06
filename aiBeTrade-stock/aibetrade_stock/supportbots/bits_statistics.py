from pymongo import MongoClient
import os
from datetime import datetime
import telebot
import logging

logger = logging.getLogger('BitsBot')

def get_statistics(bot,chat_id,lang='en'):
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
            logger.info(f"Last record: {last_record}")
            send_bot = publish_to_telegram(bot,chat_id,last_record,lang) 
            return send_bot
        else:
            return {"error": "Записи не найдены"}
            
    except Exception as e:
        return {"error": f"Ошибка при получении статистики: {str(e)}"}
    finally:
        mongo_client.close()

# Функция для публикации в Telegram
def publish_to_telegram(bot, chat_id, stst_data,lang='en'):
    logger.info(f"Publish to Telegram: {chat_id} {lang}")
    try:
        image_path = stst_data['image_path']
        days = stst_data['days']
        is_successful = stst_data['is_successful']
        profit = stst_data['profit']
        totalProfit = stst_data['totalProfit']
        strategy_name = stst_data['strategy_name']
        if is_successful:
            image_path = image_path
            if lang == 'ru':
                message_text = (
                    f"🟢 <b>ABT Bits Pro: торговый день прошел успешно!</b>\n\n"
                    f"Стратегия: <b>{strategy_name}</b>\n"
                    f"Прибыль от торговли: <b>{profit}%</b>\n"
                    f"Общая прибыль: <b>{totalProfit}%</b>\n"
                    f"Количество торговых дней: <b>{days}</b>"
                )
            elif lang == 'fra':
                message_text = (
                    f"🟢 <b>ABT Bits Pro: jour de trading réussi!</b>\n\n"
                    f"Stratégie: <b>{strategy_name}</b>\n"
                    f"Profit de la stratégie: <b>{profit}%</b>\n"
                    f"Profit total: <b>{totalProfit}%</b>\n"
                    f"Nombre de jours de trading: <b>{days}</b>"
                )
            elif lang == 'deu':
                message_text = (
                    f"🟢 <b>ABT Bits Pro: Tagestrading erfolgreich!</b>\n\n"
                    f"Strategie: <b>{strategy_name}</b>\n"
                    f"Profit der Strategie: <b>{profit}%</b>\n"
                    f"Gesamtprofit: <b>{totalProfit}%</b>\n"
                    f"Anzahl der Trading-Tage: <b>{days}</b>"
                )
            elif lang == 'esp':
                # TODO: перевести на испанский
                message_text = (
                    f"🟢 <b>ABT Bits Pro: día de trading exitoso!</b>\n\n"
                    f"Estratégia: <b>{strategy_name}</b>\n"
                    f"Profit de la estrategia: <b>{profit}%</b>\n"
                    f"Profit total: <b>{totalProfit}%</b>\n"
                    f"Número de días de trading: <b>{days}</b>"
                )
            elif lang == 'lang_zh':
                message_text = (
                    f"🟢 <b>ABT Bits Pro: 日交易成功！</b>\n\n"
                    f"策略: <b>{strategy_name}</b>\n"
                    f"交易利润: <b>{profit}%</b>\n"
                    f"总利润: <b>{totalProfit}%</b>\n"
                    f"交易天数: <b>{days}</b>"    
                )
            else:
                message_text = (
                    f"🟢 <b>ABT Bits Pro: day trading was Successful!</b>\n\n"
                    f"Strategy: <b>{strategy_name}</b>\n"
                    f"Profit of trade is: <b>{profit}%</b>\n"
                    f"Total profit: <b>{totalProfit}%</b>\n"
                    f"Number of Trading Days: <b>{days}</b>"
                )
        else:
            if lang == 'ru':
                message_text = (
                    f"🔴 <b>ABT Bits Pro: торговый день прошел неудачно!</b>\n\n"
                    f"Стратегия: <b>{strategy_name}</b>\n"
                    f"Прибыль от торговли: <b>{profit}%</b>\n"
                    f"Общая прибыль: <b>{totalProfit}%</b>\n"
                    f"Количество торговых дней: <b>{days}</b>"
                )
            elif lang == 'lang_zh':
                message_text = (
                    f"🔴 <b>ABT Bits Pro: 日交易失败！</b>\n\n"
                    f"策略: <b>{strategy_name}</b>\n"
                    f"交易利润: <b>{profit}%</b>\n"
                    f"总利润: <b>{totalProfit}%</b>\n"
                    f"交易天数: <b>{days}</b>"
                )
            elif lang == 'fra':
                # TODO: перевести на французский
                message_text = (
                    f"🔴 <b>ABT Bits Pro: jour de trading échoué !</b>\n\n"
                    f"Stratégie: <b>{strategy_name}</b>\n"
                    f"Profit de la stratégie: <b>{profit}%</b>\n"
                    f"Profit total: <b>{totalProfit}%</b>\n"
                    f"Nombre de jours de trading: <b>{days}</b>"
                )
            elif lang == 'deu':
                 # TODO: перевести на немецкий
               message_text = (
                    f"🔴 <b>ABT Bits Pro: Tagestrading fehlgeschlagen!</b>\n\n"
                    f"Strategie: <b>{strategy_name}</b>\n"
                    f"Profit der Strategie: <b>{profit}%</b>\n"
                    f"Gesamtprofit: <b>{totalProfit}%</b>\n"
                    f"Anzahl der Trading-Tage: <b>{days}</b>"
                )
            elif lang == 'esp':
                  # TODO: перевести на испанский
               message_text = (
                    f"🔴 <b>ABT Bits Pro: día de trading fallido!</b>\n\n"
                    f"Estratégia: <b>{strategy_name}</b>\n"
                    f"Profit de la estrategia: <b>{profit}%</b>\n"
                    f"Profit total: <b>{totalProfit}%</b>\n"
                    f"Número de días de trading: <b>{days}</b>"
                )
            else:
                message_text = (
                    f"🔴 <b>ABT Bits Pro: day trading was Failure!</b>\n\n"
                    f"Strategy: <b>{strategy_name}</b>\n"
                    f"Profit of trade is: <b>{profit}%</b>\n"
                    f"Total profit: <b>{totalProfit}%</b>\n"
                    f"Number of Trading Days: <b>{days}</b>"
                )
        # Публикация английского поста с картинкой
        if lang == 'ru':
            button1 = telebot.types.InlineKeyboardButton("🚀 ABT Bits Pro chanel", url="https://t.me/abtbits")
            button2 = telebot.types.InlineKeyboardButton("💼 ABT Bits Pro news", url="https://forms.gle/abtbit")
        else:
            button1 = telebot.types.InlineKeyboardButton("🚀 ABT Bits Pro chanel", url="https://t.me/abtbits")
            button2 = telebot.types.InlineKeyboardButton("💼 ABT Bits Pro news", url="https://t.me/abtbitxx")


        # Добавление кнопок в одну строку
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(button1)
        markup.add(button2)

        with open(image_path, 'rb') as photo:
            bot.send_photo(chat_id, photo, caption=message_text, reply_markup=markup, parse_mode='HTML')

        logger.info("Сообщения успешно опубликованы в Telegram.")
        return {"success": "Сообщения успешно опубликованы в Telegram."}
    except Exception as e:
        logger.error(f"Ошибка при публикации в Telegram: {e}")
        return {"error": f"Ошибка при публикации в Telegram: {e}"}
