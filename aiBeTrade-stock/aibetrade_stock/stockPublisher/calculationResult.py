import json
import os
import requests
from datetime import datetime, timedelta
from pybit.unified_trading import HTTP
import schedule
import time
import logging
from pathlib import Path
from datetime import datetime

# Настройки логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# Настройки для каждого аккаунта
accounts = [
    {
        "api_key": os.getenv('API_BYBIT_CR'),
        "api_secret": os.getenv('API_BYBIT_SEC_CR'),
        "strategy_id": "roman_strat",
        "strategy_name": "ABT BITS PRO",
        "start_deposit": 4950,  # Начальный депозит для первого аккаунта
        "channel_id": '-1002247551722'  # ID Telegram @abtbits
    },
    {
        "api_key": os.getenv('API_BYBIT_CR_1'),
        "api_secret": os.getenv('API_BYBIT_SEC_CR_1'),
        "strategy_id": "constantin_strat",
        "strategy_name": "ABT BITS PRO_NOM",
        "start_deposit": 4050,  # Начальный депозит для второго аккаунта
        "channel_id": os.getenv('ID_CH_CR')  # ID Telegram канала для второго аккаунта
    },
    {
        "api_key": os.getenv('API_BYBIT_CR_2'),
        "api_secret": os.getenv('API_BYBIT_SEC_CR_2'),
        "strategy_id": "news_strat",
        "strategy_name": "ABT BITS PRO_NEWS",
        "start_deposit": 2350,  # Начальный депозит для третьего аккаунта
        "channel_id": os.getenv('ID_CH_CR')  # ID Telegram канала для третьего аккаунта
    }
]

# Настройки для Telegram
URL_BOT = 'https://api.telegram.org/bot'
TELEGRAM_TOKEN = os.getenv('API_BOT_CR')  # Токен вашего Telegram бота

# Функция для публикации в Telegram через запрос к API
def publish_to_telegram(profit, totalProfit, days, is_successful, strategy_name, channel_id):
    response = None  # Инициализируем переменную response заранее
    try:
        # Определяем картинку и текст
        if is_successful:
            image_path = "pic/successful.jpg"
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

        # Добавляем кнопки с эмоджи и ссылками
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🎉", "callback_data": "celebrate"},
                    {"text": "🔥", "callback_data": "fire"},
                    {"text": "😎", "callback_data": "cool"},
                    {"text": "😍", "callback_data": "love"},
                    {"text": "🤩", "callback_data": "star"}
                ],
                [{"text": "🚀 ABT Bits Pro Bot", "url": "https://t.me/aibetradecombot"}],
                [{"text": "🛠⁉️ ABT Support", "url": "https://t.me/abtsupportbot"}]
            ]
        }

        url = f'{URL_BOT}{TELEGRAM_TOKEN}/sendPhoto'

        # Открываем изображение и отправляем запрос на API Telegram
        with open(image_path, 'rb') as image_file:
            files = {'photo': image_file}
            data = {
                'chat_id': channel_id,
                'caption': message_text,
                'parse_mode': 'HTML',
                'reply_markup': json.dumps(keyboard)  # Добавляем кнопки
            }
            response = requests.post(url, files=files, data=data)

        if response.status_code == 200:
            logger.info(f"Message sent to Telegram for strategy {strategy_name}.")
        else:
            logger.error(f"Failed to send message: {response.status_code}, {response.text}")
    except Exception as e:
        logger.error(f"Error publishing to Telegram: {e}")

# Функция для записи нового баланса и даты в файл
def save_balance_to_file(balance, strategy_id, filename=None):
    if filename is None:
        filename = f"balance_data_{strategy_id}.json"
    
    filepath = filename
    current_date = datetime.now().strftime('%d.%m.%Y')

    try:
        with open(filepath, 'r') as file:
            data = json.load(file)
            if isinstance(data, dict):
                data = [data]
    except FileNotFoundError:
        data = []  # Если файла нет, начинаем с пустого списка

    # Флаг для отслеживания, найдена ли запись за текущий день
    record_found = False

    # Проверяем, есть ли запись за текущий день
    for entry in data:
        if entry['date'] == current_date:
            entry['balance'] = balance  # Обновляем баланс для текущего дня
            logger.info(f"Balance for {current_date} has been updated.")
            record_found = True
            break

    # Если запись не найдена, добавляем новую
    if not record_found:
        new_entry = {'balance': balance, 'date': current_date}
        data.append(new_entry)
        logger.info(f"Balance for {current_date} has been added.")

    try:
        with open(filepath, 'w') as file:
            json.dump(data, file, indent=4)
        logger.info(f"Balance saved to {filepath}")
    except Exception as e:
        logger.error(f"Error saving balance to file: {e}")

# Функция для чтения баланса за предыдущий день
def get_previous_balance(strategy_id, filename=None):
    if filename is None:
        filename = f"balance_data_{strategy_id}.json"
    
    filepath = filename
    try:
        with open(filepath, 'r') as file:
            data = json.load(file)
            if isinstance(data, dict):
                data = [data]
            prev_date = (datetime.now() - timedelta(days=1)).strftime('%d.%m.%Y')
            for entry in data:
                if entry['date'] == prev_date:
                    return float(entry['balance'])
            logger.info(f"No balance entry found for {prev_date}.")
            return None
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return None
    except Exception as e:
        logger.error(f"Error reading balance from file: {e}")
        return None

# Функция для подсчета количества записей в файле балансов
def count_days_in_file(strategy_id, filename=None):
    if filename is None:
        filename = f"balance_data_{strategy_id}.json"
    
    filepath = filename
    try:
        with open(filepath, 'r') as file:
            data = json.load(file)
            if isinstance(data, dict):
                data = [data]
            return len(data)  # Возвращаем количество записей (количество дней)
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return 0
    except Exception as e:
        logger.error(f"Error counting days in file: {e}")
        return 0

# Функция расчета профита
def calculate_profit(resultBalance, preBalance, start_deposit):
    if preBalance is None:
        logger.warning("No previous balance data available for calculation.")
        return None, None
    
    profit = (resultBalance / preBalance - 1) * 100
    totalProfit = (resultBalance / start_deposit - 1) * 100

    logger.info(f"Текущий баланс: {resultBalance}")
    logger.info(f"Баланс предыдущий день: {preBalance}")
    logger.info(f"Результат (%): {profit}")
    logger.info(f"Общий результат (%): {totalProfit}")

    return round(profit, 2), round(totalProfit, 2)

# Основная функция для каждого аккаунта
def main_for_account(account):
    try:
        # Создаем сессию с API Bybit для каждого аккаунта
        session = HTTP(
            testnet=False,  # Используйте False, если работаете на основном API
            api_key=account["api_key"],
            api_secret=account["api_secret"]
        )
        logger.info(f'Api keys for {account["strategy_name"]}: {account["api_key"]}')

        # Получаем баланс для определенной монеты (например, USDT)
        response = session.get_wallet_balance(
            accountType="UNIFIED",
            coin="USDT"
        )

        # Логируем полный ответ от Bybit API для отладки
        logger.info(f'Full response for {account["strategy_name"]}: {json.dumps(response, indent=4)}')

        if response['retCode'] == 0:
            try:
                result_list = response['result']['list'][0]
                coin_data = result_list['coin'][0]
                resultBalance = float(coin_data['usdValue'])
                logger.info(f'Available to Withdraw for {account["strategy_name"]}: {resultBalance}')
                
                # Сохраняем баланс
                save_balance_to_file(resultBalance, account["strategy_id"])
                
                # Получаем баланс за предыдущий день
                preBalance = get_previous_balance(account["strategy_id"])

                # Подсчитываем количество записей (количество дней наблюдений)
                days = count_days_in_file(account["strategy_id"])

                # Рассчитываем профит
                profit, totalProfit = calculate_profit(resultBalance, preBalance, account["start_deposit"])
                
                if profit is not None and totalProfit is not None:
                    # Определяем успех или провал и публикуем сообщение в Telegram
                    is_successful = resultBalance > preBalance
                    publish_to_telegram(profit, totalProfit, days, is_successful, account["strategy_name"], account["channel_id"])
                
            except (KeyError, IndexError) as e:
                logger.error(f'Error extracting resultBalance: {e}')
        else:
            logger.error(f'Error in response for {account["strategy_name"]}: {response["retMsg"]}')
    except Exception as e:
        logger.error(f"Error in Bybit API session for {account['strategy_name']}: {e}")

# Функция для ожидания до 9 утра
def wait_until_9am():
    now = datetime.now()
    target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)

    # Если текущее время уже прошло 9:00, ждем до 9 утра следующего дня
    if now > target_time:
        target_time += timedelta(days=1)

    # Вычисляем, сколько времени осталось до 9 утра
    time_to_wait = (target_time - now).total_seconds()
    logger.info(f"Waiting until 9 AM. Time to wait: {time_to_wait // 3600} hours and {(time_to_wait % 3600) // 60} minutes")
    
    time.sleep(time_to_wait)

# Основной код, который будет выполнен только в 9 утра
if __name__ == "__main__":
    while True:
        # Ждем до 9 утра
        wait_until_9am()

        # Запускаем основную задачу
        main()

        # После выполнения основной задачи ждем до следующего 9 утра