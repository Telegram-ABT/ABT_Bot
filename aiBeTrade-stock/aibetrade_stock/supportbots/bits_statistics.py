from pymongo import MongoClient
import os
from datetime import datetime
import telebot
import logging

logger = logging.getLogger('BitsBot')
mongo_client = MongoClient(os.getenv('MONGO_URL_SERV'))
db = mongo_client["nntcapital"]
collection = db["bits_data_trade"]


def get_statistics_user_trade(bot,chat_id,message_id,lang='en'):
    try:
        # Удаляем предыдущее сообщение с кнопками
        try:
            bot.delete_message(chat_id, message_id)
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            
        strategy_id = "roman_strat"
        last_record = collection.find_one(
            {"strategy_id": strategy_id},  # пустой фильтр для выбора всех документов
            sort=[("date", -1)]  # сортировка по date в обратном порядке
        )
        return last_record
    except Exception as e:
        return {"error": f"Ошибка при получении статистики: {str(e)}"}


def get_statistics_system(bot, chat_id, message_id, lang='en'):
    try:
        # Удаляем предыдущее сообщение с кнопками
        try:
            bot.delete_message(chat_id, message_id)
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            
        # Подключение к MongoDB
        strategy_id = "roman_strat"
        
        # Получаем последнюю запись, сортируя по полю date в обратном порядке
        last_record = collection.find_one(
            {"strategy_id": strategy_id},
            sort=[("date", -1)]
        )
        
        if last_record:
            logger.info(f"Last record: {last_record}")
            send_bot = publish_to_telegram(bot, chat_id, last_record, lang)
            
            # После успешной отправки статистики показываем меню
            if "success" in send_bot:
                header_texts = {
                    'ru': '📊 Выберите действие:',
                    'en': '📊 Choose action:',
                    'fr': '📊 Choisissez une action:',
                    'de': '📊 Aktion wählen:',
                    'es': '📊 Elija una acción:',
                    'zh': '📊 选择操作：'
                }
                
                markup = create_statistics_menu(bot, chat_id, lang)
                bot.send_message(
                    chat_id,
                    header_texts.get(lang, header_texts['en']),
                    reply_markup=markup
                )
            
            return send_bot
        else:
            return {"error": "Записи не найдены"}
            
    except Exception as e:
        return {"error": f"Ошибка при получении статистики: {str(e)}"}


def create_statistics_menu(bot,chat_id,lang='en'):
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
    date_format = "%Y-%m-%d"
    
    texts = {
        'ru': {
            'nickname': 'Название',
            'date_end': 'Дата окончания',
            'deposit_end': 'Конечный депозит',
            'deposit_start': 'Начальный депозит',
            'date_pay': 'Дата оплаты',
            'share_profit': 'Доля прибыли',
            'refferal': 'Реферальный ранг',
            'date_start': 'Дата начала',
            'percent_profit': '% прибыли',
            'profit': 'Прибыль',
            'share_profit_rank': 'Ставка комиссии',
            'count_pay_day': 'Дней до оплаты'
        },
        'en': {
            'nickname': 'Nickname',
            'date_end': 'End Date',
            'deposit_end': 'Final Deposit',
            'deposit_start': 'Initial Deposit',
            'date_pay': 'Payment Date',
            'share_profit': 'Profit Share',
            'refferal': 'Referral Rank',
            'date_start': 'Start Date',
            'percent_profit': 'Profit %',
            'profit': 'Profit',
            'share_profit_rank': 'Commission Share',
            'count_pay_day': 'Days to pay'
        },
        # TODO: перевести на французский
        'fr': {
            'nickname': 'Nom d\'utilisateur',
            'date_start': 'Date de début',
            'date_end': 'Date de fin',
            'deposit_start': 'Dépôt initial',
            'deposit_end': 'Dépôt final',
            'date_pay': 'Date de paiement',
            'share_profit': 'Part de profit',
            'refferal': 'Rang de référencement',
            'percent_profit': '% de profit',
            'profit': 'Profit',
            'share_profit_rank': 'Commission de profit',
            'count_pay_day': 'Jours avant le paiement'
        },
        # TODO: перевести на немецкий
        'de': {
            'nickname': 'Benutzername',
            'date_end': 'End Datum',
            'deposit_end': 'Endkapital',
            'deposit_start': 'Anfangskapital',
            'date_pay': 'Zahlungsdatum',
            'share_profit': 'Profitanteil',
            'refferal': 'Referenz-Rang',
            'date_start': 'Start Datum',
            'percent_profit': 'Profit %',
            'profit': 'Profit',
            'share_profit_rank': 'Gewinnanteil',
            'count_pay_day': 'Tage bis zur Zahlung'
        },
        # TODO: перевести на китайский
        'zh': {
            'nickname': '昵称',
            'date_end': '结束日期',
            'deposit_end': '最终存款',
            'deposit_start': '初始存款',
            'date_pay': '付款日期',
            'share_profit': '利润份额',
            'refferal': '推荐等级',
            'date_start': '开始日期',
            'percent_profit': '%利润',
            'profit': '利润',
            'share_profit_rank': '佣金份额',
            'count_pay_day': '天数到付款'
        },
        # TODO: перевести на испанский
        'es': {
            'nickname': 'Nombre de usuario',
            'date_end': 'Fecha de finalización',
            'deposit_end': 'Depósito final',
            'deposit_start': 'Depósito inicial',
            'date_pay': 'Fecha de pago',
            'share_profit': 'Parte de la ganancia',
            'refferal': 'Rango de referido',
            'date_start': 'Fecha de inicio',
            'percent_profit': 'Porcentaje de ganancia',
            'profit': 'Ganancia',
            'share_profit_rank': 'Comisión de ganancia',
            'count_pay_day': 'Días antes del pago'
        }
    }
    t = texts.get(lang, texts['en'])

    for robot in robot_data:
        
    
        
        return (
            f"----------------------------------\n"
            f"{t['nickname']}: <b>{robot['nickname']}</b>\n"
            f"{t['date_start']}: {robot['date_start'].strftime(date_format)}\n"
            f"{t['deposit_start']}: <b>{robot['deposit_start']}</b> usdt\n"
            if robot['is_pay']
              f"🟢 Close period\n" 
              f"{t['date_end']}: {robot['date_end'].strftime(date_format)}\n"
              f"{t['deposit_end']}: <b>{robot['deposit_end']}</b> usdt\n"
              profit = float(robot['deposit_end']) - float(robot['deposit_start'])
              persent_profit = profit / float(robot['deposit_start']) * 100
              share_profit = profit * float(robot['share_profit_rank'])/100
              f"{t['profit']}: <b>{profit:2f} usdt ({persent_profit:2f}%)</b>\n"
              f"{t['share_profit']}: <b>{share_profit:2f} usdt</b>\n"
              f"{t['date_pay']}: {robot['date_pay'].strftime(date_format)}\n"
            
            elif robot['is_pay']== False and robot['calc_ready']:
              f"🔴 wait payments\n"
              f"{t['date_end']}: {robot['date_end'].strftime(date_format)}\n"
              f"{t['deposit_end']}: <b>{robot['deposit_end']}</b> usdt\n"
              profit = float(robot['deposit_end']) - float(robot['deposit_start'])
              persent_profit = profit / float(robot['deposit_start']) * 100
              share_profit = profit * float(robot['share_profit_rank'])/100
              f"{t['profit']}: <b>{profit:2f} usdt ({persent_profit:2f}%)</b>\n"
              f"{t['share_profit']}: <b>{share_profit:2f} usdt</b>\n"
              f"{t['date_pay']}: {robot['date_pay'].strftime(date_format)}\n"
            else:
                f"⚪ in progress...\n"
                if float(robot['deposit_start']) < 10000:
                    count_date_pay = 30
                elif float(robot['deposit_start']) < 10000 and float(robot['deposit_start']) >= 1000:
                    count_date_pay = 60
                else
                    count_date_pay = 90
                date_pay = robot['date_start']+timedelta(days=count_date_pay)
                # TODO: Формат даты без времени
                f"{t['date_pay']}: <b>{date_pay.strftime(date_format)} ({date_pay-datetime.now().date()} days)</b>\n"

        )

def get_statistics(bot, chat_id, message_id, lang='en'):
    """Основная функция статистики"""
    bot.delete_message(chat_id, message_id)
    try:
        # Создаем и отправляем меню статистики
        markup = create_statistics_menu(bot,chat_id,lang)
        
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
