from pymongo import MongoClient
import os
from datetime import datetime
import telebot
import logging

logger = logging.getLogger('BitsBot')
mongo_client = MongoClient(os.getenv('MONGO_URL_SERV'))
db = mongo_client["nntcapital"]
collection = db["bits_data_trade"]


def get_statistics_user_trade(bot,chat_id,lang='en'):
    try:
        strategy_id = "roman_strat"
        last_record = collection.find_one(
            {"strategy_id": strategy_id},  # пустой фильтр для выбора всех документов
            sort=[("date", -1)]  # сортировка по date в обратном порядке
        )
        return last_record
    except Exception as e:
        return {"error": f"Ошибка при получении статистики: {str(e)}"}


def get_statistics_system(bot,chat_id,lang='en'):
    try:
        # Подключение к MongoDB
        strategy_id = "roman_strat"
        
        # Получаем последнюю запись, сортируя по полю date в обратном порядке
        last_record = collection.find_one(
            {"strategy_id": strategy_id},  # пустой фильтр для выбора всех документов
            sort=[("date", -1)]  # сортировка по date в обратном порядке
        )
        
        if last_record:
            logger.info(f"Last record: {last_record}")
            send_bot = publish_to_telegram(bot,chat_id,last_record,lang) 
            markup = create_statistics_menu(lang)
            return markup
        else:
            markup = create_statistics_menu(lang)
            return markup
            
    except Exception as e:
        return {"error": f"Ошибка при получении статистики: {str(e)}"}
    finally:
        mongo_client.close()


def create_statistics_menu(lang='en'):
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    # Тексты для кнопок на разных языках
    button_texts = {
        'ru': {
            'trading': '📊 Торговый результат',
            'robots': '🤖 Мои роботы',
            'back': '⬅️ Назад'
        },
        'en': {
            'trading': '📊 Trading Result',
            'robots': '🤖 My Robots',
            'back': '⬅️ Back'
        },
        'fr': {
            'trading': '📊 Résultat du Trading',
            'robots': '🤖 Mes Robots',
            'back': '⬅️ Retour'
        },
        'de': {
            'trading': '📊 Handelsergebnis',
            'robots': '🤖 Meine Roboter',
            'back': '⬅️ Zurück'
        },
        'es': {
            'trading': '📊 Resultado de Trading',
            'robots': '🤖 Mis Robots',
            'back': '⬅️ Volver'
        },
        'zh': {
            'trading': '📊 交易结果',
            'robots': '🤖 我的机器人',
            'back': '⬅️ 返回'
        }
    }

    texts = button_texts.get(lang, button_texts['en'])
    
    # Добавляем кнопку торгового результата
    markup.add(telebot.types.InlineKeyboardButton(
        texts['trading'], 
        callback_data='stats_trading'
    ))
    
    # Проверяем наличие записей в bits_user_trade
    user_robots = db["bits_user_trade"].distinct("nickname")
    if user_robots:
        markup.add(telebot.types.InlineKeyboardButton(
            texts['robots'], 
            callback_data='stats_robots'
        ))
    
    # Добавляем кнопку "Назад"
    markup.add(telebot.types.InlineKeyboardButton(
        texts['back'], 
        callback_data='stats_back'
    ))
    
    return markup

def create_robots_menu(nicknames, lang='en'):
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    # Добавляем кнопку для каждого никнейма
    for nickname in nicknames:
        markup.add(telebot.types.InlineKeyboardButton(
            f"🤖 {nickname}", 
            callback_data=f'robot_{nickname}'
        ))
    
    # Добавляем кнопку "Назад" в меню статистики
    back_texts = {
        'ru': '⬅️ Назад',
        'en': '⬅️ Back',
        'fr': '⬅️ Retour',
        'de': '⬅️ Zurück',
        'es': '⬅️ Volver',
        'zh': '⬅️ 返回'
    }
    markup.add(telebot.types.InlineKeyboardButton(
        back_texts.get(lang, back_texts['en']), 
        callback_data='stats_menu'
    ))
    
    return markup

def format_robot_stats(robot_data, lang='en'):
    # Форматирование данных робота для разных языков
    date_format = "%Y-%m-%d %H:%M:%S"
    
    texts = {
        'ru': {
            'nickname': 'Никнейм',
            'date_end': 'Дата окончания',
            'deposit_end': 'Конечный депозит',
            'deposit_start': 'Начальный депозит',
            'date_pay': 'Дата оплаты',
            'share_profit': 'Доля прибыли',
            'refferal': 'Реферальный ранг'
        },
        'en': {
            'nickname': 'Nickname',
            'date_end': 'End Date',
            'deposit_end': 'Final Deposit',
            'deposit_start': 'Initial Deposit',
            'date_pay': 'Payment Date',
            'share_profit': 'Profit Share',
            'refferal': 'Referral Rank'
        }
        # Добавьте переводы для других языков...
    }
    
    t = texts.get(lang, texts['en'])
    
    return (
        f"{t['nickname']}: {robot_data['nickname']}\n"
        f"{t['date_end']}: {robot_data['date_end'].strftime(date_format)}\n"
        f"{t['deposit_end']}: {robot_data['deposit_end']}\n"
        f"{t['deposit_start']}: {robot_data['deposit_start']}\n"
        f"{t['date_pay']}: {robot_data['date_pay'].strftime(date_format)}\n"
        f"{t['share_profit']}: {robot_data['share_profit_rank']}\n"
        f"{t['refferal']}: {robot_data['refferal_rank']}"
    )

def get_statistics(bot, chat_id, lang='en'):
    """Основная функция статистики"""
    try:
        # Создаем и отправляем меню статистики
        markup = create_statistics_menu(lang)
        
        # Тексты заголовка для разных языков
        menu_texts = {
            'ru': "📊 Статистика\nВыберите нужное действие:",
            'en': "📊 Statistics\nPlease select an action:",
            'fr': "📊 Statistiques\nVeuillez sélectionner une action:",
            'de': "📊 Statistiken\nBitte wählen Sie eine Aktion:",
            'es': "📊 Estadísticas\nPor favor, seleccione una acción:",
            'zh': "📊 统计\n请选择操作："
        }
        
        # Отправляем приветствие и меню на языке пользователя
        bot.send_message(
            chat_id,
            f"{menu_texts.get(lang, menu_texts['en'])}",
                reply_markup=markup
        )
        
        return {"success": "Menu sent successfully"}
    except Exception as e:
        logger.error(f"Error in get_statistics: {e}")
        return {"error": f"Error in get_statistics: {str(e)}"}

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
            elif lang == 'fr':
                message_text = (
                    f"🟢 <b>ABT Bits Pro: jour de trading réussi!</b>\n\n"
                    f"Stratégie: <b>{strategy_name}</b>\n"
                    f"Profit de la stratégie: <b>{profit}%</b>\n"
                    f"Profit total: <b>{totalProfit}%</b>\n"
                    f"Nombre de jours de trading: <b>{days}</b>"
                )
            elif lang == 'de':
                message_text = (
                    f"🟢 <b>ABT Bits Pro: Tagestrading erfolgreich!</b>\n\n"
                    f"Strategie: <b>{strategy_name}</b>\n"
                    f"Profit der Strategie: <b>{profit}%</b>\n"
                    f"Gesamtprofit: <b>{totalProfit}%</b>\n"
                    f"Anzahl der Trading-Tage: <b>{days}</b>"
                )
            elif lang == 'es':
                # TODO: перевести на испанский
                message_text = (
                    f"🟢 <b>ABT Bits Pro: día de trading exitoso!</b>\n\n"
                    f"Estratégia: <b>{strategy_name}</b>\n"
                    f"Profit de la estrategia: <b>{profit}%</b>\n"
                    f"Profit total: <b>{totalProfit}%</b>\n"
                    f"Número de días de trading: <b>{days}</b>"
                )
            elif lang == 'zh':
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
            elif lang == 'zh':
                message_text = (
                    f"🔴 <b>ABT Bits Pro: 日交易失败！</b>\n\n"
                    f"策略: <b>{strategy_name}</b>\n"
                    f"交易利润: <b>{profit}%</b>\n"
                    f"总利润: <b>{totalProfit}%</b>\n"
                    f"交易天数: <b>{days}</b>"
                )
            elif lang == 'fr':
                # TODO: перевести на французский
                message_text = (
                    f"🔴 <b>ABT Bits Pro: jour de trading échoué !</b>\n\n"
                    f"Stratégie: <b>{strategy_name}</b>\n"
                    f"Profit de la stratégie: <b>{profit}%</b>\n"
                    f"Profit total: <b>{totalProfit}%</b>\n"
                    f"Nombre de jours de trading: <b>{days}</b>"
                )
            elif lang == 'de':
                 # TODO: перевести на немецкий
               message_text = (
                    f"🔴 <b>ABT Bits Pro: Tagestrading fehlgeschlagen!</b>\n\n"
                    f"Strategie: <b>{strategy_name}</b>\n"
                    f"Profit der Strategie: <b>{profit}%</b>\n"
                    f"Gesamtprofit: <b>{totalProfit}%</b>\n"
                    f"Anzahl der Trading-Tage: <b>{days}</b>"
                )
            elif lang == 'es':
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
            button2 = telebot.types.InlineKeyboardButton("💼 ABT Bits Pro news", url="https://t.me/abtbit")
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
