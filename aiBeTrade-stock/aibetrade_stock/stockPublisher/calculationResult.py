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
        "strategy_name": "ABT BITS PRO_PAR",
        "start_deposit": 4920,  # Начальный депозит для первого аккаунта 
        "channel_id": os.getenv('ID_CH_CR')  # ID Telegram канала для первого аккаунта
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

        # Добавляем кнопки с ссылками
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🚀 ABT Bits Pro Bot", "url": "https://t.me/aibetradecombot"},
                    {"text": "🛠⁉️ ABT Support", "url": "https://t.me/abtsupportbot"}
                ]
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
                'reply_markup': json.dumps(keyboard)
            }
            response = requests.post(url, files=files, data=data)

        if response.status_code == 200:
            logger.info(f"Message sent to Telegram for strategy {strategy_name}.")
        else:
            logger.error(f"Failed to send message: {response.status_code}, {response.text}")
    except Exception as e:
        logger.error(f"Error publishing to Telegram: {e}")

# Остальные функции остались неизменными: save_balance_to_file, get_previous_balance, count_days_in_file, calculate_profit

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

# Планирование выполнения задачи каждые 60 минут
def main():
    for account in accounts:
        main_for_account(account)

schedule.every(60).minutes.do(main)

# Выполняем основную функцию
main()

# Бесконечный цикл для планирования задач
while True:
    schedule.run_pending()
    time.sleep(60)  # Проверяем задачи каждую минуту
