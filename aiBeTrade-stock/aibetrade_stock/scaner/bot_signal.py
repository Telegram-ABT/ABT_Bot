import os
import requests
import json
from requests.auth import HTTPBasicAuth
from pymongo import MongoClient
from datetime import datetime
from openai import OpenAI
import asyncio
import openai

# Настройки для OpenAI API
key = os.environ.get('OPENAI_API_KEY')
client_openai = OpenAI(api_key=key)

# Подключение к MongoDB
mongo_url = os.getenv('MONGO_URL_SERV')
mongo_client = MongoClient(mongo_url)
db = mongo_client["nntcapital"]
signal_collection = db["kogan_signal"]
case_collection = db["kogan_case"]

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
        print(f"Ошибка при отпвке запроса в ChatGPT: {e}")
        return None

# Функция для отправки текста в ChatGPT и получения ответа
def get_price_gpt(share):
    openai.api_key = key

    try:
        gpt_response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"Найди в интернете последнюю цену акции {share}"},
            {"role": "user", "content": "Верни только цену с разделителем дробной части точка, если цена не найдена верни 0"}
        ],
        plugins=["web_search"]
        )
        gpt_response = gpt_response['choices'][0]['message']['content']
        return None if gpt_response == "0" else float(gpt_response)
    except Exception as e:
        print(f"Ошибка при отпвке запроса в ChatGPT: {e}")
        return None

# Функция для получения текущей цены акции через Alpha Vantage
def get_stock_price_from_alpha_vantage(symbol, alpha_vantage):
    ticker = symbol.split('.')[0]
    # alpha_vantage = '76478DBVK1EF8HY1' #8HLGJJD9X394CZHY'
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={ticker}&interval=1min&apikey={alpha_vantage}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        print(data)
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

# Функция для получения текущей цены акции через брокера
def get_stock_price_from_broker(symbol, application_id, application_access_key, api_url):
    headers = {
        "Accept": "application/x-json-stream"  # Указываем тип данных, который ожидаем получить
    }
    try:
        response = requests.get(
            f"{api_url}3.0/feed/trades/{symbol}", headers=headers,
            auth=HTTPBasicAuth(application_id, application_access_key)
        )
        if response.status_code == 200:
            data = response.json()
            return float(data['price'])
        else:
            print(f"Ошибка при получении цены акции {symbol} через брокера: {response.text}")
            return None
    except Exception as e:
        print(f"Ошибка при запросе цены акции {symbol} через брокера: {e}")
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
            case_info = case_collection.find_one({"case_name": case})
            if case_info:
                # Получение текущей цены акции через Alpha Vantage
                alpha_vantage = case_info.get("alpha_vantage")
                price = get_stock_price_from_alpha_vantage(share,alpha_vantage)
                print(f"Цена акции {share} получена через Alpha Vantage: {price}")
                if price is None:
                    print(f"Не удалось получить цену для акции {share} через Alpha Vantage.")
                # Попытка получить цену через брокера
                    if case_info:
                        application_id = case_info.get("application_id")
                        application_access_key = case_info.get("application_access_key")
                        api_url = case_info.get("api_url_date")
                        price = get_stock_price_from_broker(share, application_id, application_access_key, api_url)
                
                if price is None:
                    print(f"Не удалось получить цену для акции {share} через брокера.")
                    price = 0
                    status_signal = "no_price"
                else:
                    print(f"Цена акции {share} получена: {price}")
                    status_signal = "setting"
            
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

# Функция для обновления цены акций с status_signal="no_price"
async def process_set_price_message():
    # Получение всех записей с status_signal="no_price"
    signals = signal_collection.find({"status_signal": "no_price"})
    
    for signal in signals:
        share = signal['share']
        case_name = signal['case_name']
        price = None
        case_info = case_collection.find_one({"case_name": case_name})
        if case_info:
            alpha_vantage = case_info.get("alpha_vantage")
            # Получение текущей цены акции
            # Пока закомментим  price = get_stock_price_from_alpha_vantage(share, alpha_vantage)
            if price is None:
                case_info = case_collection.find_one({"case_name": case_name})
                if case_info:
                    application_id = case_info.get("application_id")
                    application_access_key = case_info.get("application_access_key")
                    api_url = case_info.get("api_url_date")
                    # Пока закомментим price = get_stock_price_from_broker(share, application_id, application_access_key, api_url)
                if price is None:
                    print(f"Цена для акции {share} не найдена, попробуем получить через GPT")
                    price = get_price_gpt(share)

                if price is not None:
                    # Обновление записи в таблице kogan_signal
                    signal_collection.update_one(
                        {"_id": signal["_id"]},
                        {"$set": {"price": price, "status_signal": "setting"}}
                    )
                    print(f"Цена для акции {share} обновлена: {price}")
                else:
                    print(f"Не удалось обновить цену для акции {share} в портфеле {case_name}.")
        else:
            print(f"Не удалось найти информацию о брокере для портфеля {case_name}.")
        # Добавляем задержку между запросами
        await asyncio.sleep(15)  # 12 секунд задержки между запросами

# Функция для обновления статуса сигналов с "setting" на "new"
async def process_set_new_message():
    try:
        # Получение всех записей с status_signal="setting"
        signals = signal_collection.find({"status_signal": "setting"})
        
        # Обновление статуса каждой записи на "new"
        for signal in signals:
            signal_id = signal["_id"]
            signal_collection.update_one(
                {"_id": signal_id},
                {"$set": {"status_signal": "new"}}
            )
            print(f"Статус сигнала для акции {signal['share']} обновлен на 'new'.")
    except Exception as e:
        print(f"Ошибка при обновлении статуса сигналов: {e}")

# Функция для обновления статуса сигналов с "complete" на "new"
async def process_set_complete_message():
    try:
        # Получение всех записей с status_signal="setting"
        signals = signal_collection.find({"status_signal": "complete"})
        
        # Обновление статуса каждой записи на "new"
        for signal in signals:
            signal_id = signal["_id"]
            signal_collection.update_one(
                {"_id": signal_id},
                {"$set": {"status_signal": "new"}}
            )
            print(f"Статус сигнала для акции {signal['share']} обновлен на 'new'.")
    except Exception as e:
        print(f"Ошибка при обновлении статуса сигналов: {e}")

# Пример вызова фун��ции 
# asyncio.run(process_set_signal_message("#set_signal\nPortfolio1, AAPL, BUY, 50\nPortfolio2, TSLA, SELL, 30"))
# asyncio.run(process_set_price_message())
# asyncio.run(process_set_new_message())
