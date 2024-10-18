import json
import os
import requests
from datetime import datetime, timedelta
from pybit.unified_trading import HTTP
from pathlib import Path

# Настройки из переменных окружения для Telegram
URL_BOT = 'https://api.telegram.org/bot'
TELEGRAM_TOKEN = '7212356676:AAFtz6Jve66Lzq_l4BajmPnNMhL5UzSdnps'  # Токен вашего Telegram бота
CHANNEL_ID = '-1002238309807' # ID вашего канала
script_directory = Path(__file__).parent  # Путь к каталогу исполняемого файла

# Функция для публикации в Telegram через запрос к API
def publish_to_telegram(profit, totalProfit, days, is_successful):
    # Определяем картинку и текст
    if is_successful:
        image_path = script_directory / "pic/successful.jpg"
        message_text = (
            f"🟢 <b>ABT Bits: day trading was Successful!</b>\n\n"
            f"Strategy: <b>ABT BITS PRO</b>\n"
            f"Profit of trade is: <b>{profit}%</b>\n"
            f"Total profit: <b>{totalProfit}%</b>\n"
            f"Number of Trading Days: <b>{days}</b>"
        )
    else:
        image_path = script_directory / "pic/failure.jpg"
        message_text = (
            f"🔴 <b>ABT Bits: day trading was Failure!</b>\n\n"
            f"Strategy: <b>ABT BITS PRO</b>\n"
            f"Profit of trade is: <b>{profit}%</b>\n"
            f"Total profit: <b>{totalProfit}%</b>\n"
            f"Number of Trading Days: <b>{days}</b>"
        )

    url = f'{URL_BOT}{TELEGRAM_TOKEN}/sendPhoto'

    # Открываем изображение и отправляем запрос на API Telegram
    with open(image_path, 'rb') as image_file:
        files = {'photo': image_file}
        data = {
            'chat_id': CHANNEL_ID,
            'caption': message_text,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, files=files, data=data)

    if response.status_code == 200:
        print(f"Message sent to Telegram channel {CHANNEL_ID}.")
    else:
        print(f"Failed to send message: {response.status_code}, {response.text}")

# Функция для записи нового баланса и даты в файл
def save_balance_to_file(balance, filename="balance_data.json"):
    filepath = script_directory / filename
    current_date = datetime.now().strftime('%d.%m.%Y')

    try:
        with open(filepath, 'r') as file:
            data = json.load(file)
            if isinstance(data, dict):
                data = [data]
    except FileNotFoundError:
        data = []  # Если файла нет, начинаем с пустого списка

    # Проверяем, есть ли запись за текущий день
    for entry in data:
        if entry['date'] == current_date and entry['balance'] == balance:
            print(f"Balance for {current_date} has not changed. No new entry added.")
            return

    # Добавляем новую запись
    new_entry = {'balance': balance, 'date': current_date}
    data.append(new_entry)

    # Записываем обновленный список в файл
    with open(filepath, 'w') as file:
        json.dump(data, file, indent=4)

    print(f"Balance saved to {filepath}")

# Функция для чтения баланса за предыдущий день
def get_previous_balance(filename="balance_data.json"):
    filepath = script_directory / filename
    try:
        with open(filepath, 'r') as file:
            data = json.load(file)
            if isinstance(data, dict):
                data = [data]
            prev_date = (datetime.now() - timedelta(days=1)).strftime('%d.%m.%Y')
            for entry in data:
                if entry['date'] == prev_date:
                    return float(entry['balance'])
            return None
    except FileNotFoundError:
        return None

# Функция для подсчета количества записей в файле балансов
def count_days_in_file(filename="balance_data.json"):
    filepath = script_directory / filename
    try:
        with open(filepath, 'r') as file:
            data = json.load(file)
            if isinstance(data, dict):
                data = [data]
            return len(data)  # Возвращаем количество записей (количество дней)
    except FileNotFoundError:
        return 0

# Функция расчета профита
def calculate_profit(resultBalance, preBalance):
    if preBalance is None:
        print("No previous balance data available for calculation.")
        return None, None
    
    profit = (resultBalance / preBalance - 1) * 100
    totalProfit = (resultBalance / 5000 - 1) * 100
    
    return round(profit, 2), round(totalProfit, 2)

# Создаем сессию с API Bybit
session = HTTP(
    testnet=False,  # Используйте False, если работаете на основном API
    api_key = "BLHHwcap6tcf4PqmcN",
    api_secret = "LPd4Lcjk5vOHMoJ81I1oedmH2rSlOhasQrYD"
)

# Получаем баланс для определенной монеты (например, USDT)
response = session.get_wallet_balance(
    accountType="UNIFIED",
    coin="USDT"
)

if response['retCode'] == 0:
    try:
        result_list = response['result']['list'][0]
        coin_data = result_list['coin'][0]
        resultBalance = float(coin_data['availableToWithdraw'])
        print(f'Available to Withdraw: {resultBalance}')
        
        # Сохраняем баланс
        save_balance_to_file(resultBalance)
        
        # Получаем баланс за предыдущий день
        preBalance = get_previous_balance()

        # Подсчитываем количество записей (количество дней наблюдений)
        days = count_days_in_file()

        # Рассчитываем профит
        profit, totalProfit = calculate_profit(resultBalance, preBalance)
        
        if profit is not None and totalProfit is not None:
            # Определяем успех или провал и публикуем сообщение в Telegram
            is_successful = resultBalance > preBalance
            publish_to_telegram(profit, totalProfit, days, is_successful)
        
    except (KeyError, IndexError) as e:
        print(f'Error extracting resultBalance: {e}')
else:
    print(f'Error in response: {response["retMsg"]}')
