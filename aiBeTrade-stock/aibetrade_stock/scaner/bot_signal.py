import os
import requests
import json
from requests.auth import HTTPBasicAuth
from pymongo import MongoClient
from datetime import datetime
from openai import OpenAI
import asyncio

# Настройки для OpenAI API
key = os.environ.get('OPENAI_API_KEY')
client_openai = OpenAI(api_key=key)

# Подключение к MongoDB
mongo_url = os.getenv('MONGO_URL_SERV')
mongo_client = MongoClient(mongo_url)
db = mongo_client["nntcapital"]
signal_collection = db["kogan_signal"]

# Функция для отправки текста в ChatGPT и получения ответа
def send_to_chatgpt(prompt, text):
    try:
        print(f"Отправка в ChatGPT: Промт: {prompt}, Текст: {text}")
        response = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ]
        )
        gpt_response = response.choices[0].message.content.strip()
        return gpt_response
    except Exception as e:
        print(f"Ошибка при отправке запроса в ChatGPT: {e}")
        return None

# Функция для получения текущей цены акции через Alpha Vantage
def get_stock_price_from_alpha_vantage(symbol):
    ticker = symbol.split('.')[0]
    alpha_vantage = '8HLGJJD9X394CZHY'
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={ticker}&interval=1min&apikey={alpha_vantage}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        try:
            last_refreshed = data['Meta Data']['3. Last Refreshed']
            last_price = data['Time Series (1min)'][last_refreshed]['4. close']
            return float(last_price)
        except KeyError:
            print(f"Ошибка при получении данных о цене акции {ticker}.")
            return None
    else:
        print(f"Ошибка при получении цены акции {ticker}: {response.text}")
        return None

# Основная функция для обработки сообщений с #set_signal
async def process_set_signal_message(message_text):
    lines = message_text.split('\n')
    for line in lines:
        if not line.strip():
            continue
        try:
            case, share, type_op, balance = line.split(',')
            share = share.strip()
            balance = float(balance.strip())
        except Exception as e:
            print(f"Ошибка при разборе строки: {e}")
            continue

        # Запрос в ChatGPT для получения биржи
        promt = f"Найди биржу, где торгуется акция {share}, и верни ответ в строгом формате Тикер.Биржа. Если биржу определить не удалось верни только название акции"
        gpt_response = send_to_chatgpt(promt, share)

        if gpt_response:
            share = gpt_response.strip()

            # Получение текущей цены акции через Alpha Vantage
            price = get_stock_price_from_alpha_vantage(share)
            if price is None:
                print(f"Не удалось получить цену для акции {share}.")
                price = 0
                status_signal = "no price"
            else:
                print(f"Цена акции {share} получена: {price}")
                status_signal = ""setting""
            # Создание записи в таблице kogan_signal
            signal_data = {
                "date": datetime.now(),
                "case_name": case,
                "share": share,
                "type": type_op,
                "price": price,
                "balance": balance,
                "status_signal": status_signal
            }
            signal_collection.insert_one(signal_data)
            print(f"Сигнал для акции {share} успешно создан и сохранен в базе данных.")

# Пример вызова функции 
# asyncio.run(process_set_signal_message("#set_signal\nPortfolio1, AAPL, BUY, 50\nPortfolio2, TSLA, SELL, 30"))
