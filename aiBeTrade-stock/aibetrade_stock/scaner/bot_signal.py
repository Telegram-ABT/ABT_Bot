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
case_collection = db["kogan_case"]
case_share_collection = db["kogan_case_share"]

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
    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"Найди в интернете последнюю цену акции {share}"},
                {"role": "user", "content": "Верни только цену с разделителем дробной части точка, если цена не найдена верни 0"}
            ], plugins=["web_search"]
        )
        gpt_response = response.choices[0].message.content.strip()
        return None if gpt_response == "0" else float(gpt_response)
    except Exception as e:
        print(f"Ошибка при отпвке запроса в ChatGPT: {e}")
        return None

# Функция для получения текущей цены акции через Alpha Vantage
def get_stock_price_from_alpha_vantage(symbol, alpha_vantage):
    ticker = symbol.split('.')[0]
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
        "Accept": "application/x-json-stream"
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
                price = get_stock_price_from_alpha_vantage(share, alpha_vantage)
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
            price = get_stock_price_from_alpha_vantage(share, alpha_vantage)
            if price is None:
                case_info = case_collection.find_one({"case_name": case_name})
                if case_info:
                    application_id = case_info.get("application_id")
                    application_access_key = case_info.get("application_access_key")
                    api_url = case_info.get("api_url_date")
                    price = get_stock_price_from_broker(share, application_id, application_access_key, api_url)
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

# Функция для получения статуса сигналов
async def process_get_status2_message():
    text_message = await process_get_status_message()
    print(text_message)

async def process_get_status_message():
    print("Начало выполнения process_get_status_message")
    
    # 1. Выбираем активные записи из таблицы kogan_case
    active_cases = case_collection.find({"get_status": True})
    print(f"Найде��о активных записей: {active_cases.count()}")

    # 2. Обновляем записи в kogan_case_share, устанавливая get_status = False
    reset_get_status_in_shares([case['case_name'] for case in active_cases])
    print("Обновлены записи в kogan_case_share, get_status установлен в False")

    text_message = "Начало запроса данных с брокера.\n"

    for case in active_cases:
        print(f"Обработка портфеля: {case['case_name']}")
        
        # 3. Делаем запрос к брокеру
        response = await get_broker_info(case['account_id'], case['application_id'], case['application_access_key'], case['api_url_date'])
        if response is None:
            error_message = f"Ошибка при получении информации о портфеле {case['case_name']}."
            print(error_message)
            text_message += error_message + "\n"
            continue
        
        portfolio_info = response.json()
        print(f"Получена информация о портфеле: {portfolio_info}")
        text_message += f"Получена информация о портфеле: {portfolio_info}\n"

        # 4. Формируем начальную часть сообщения
        text_message += f"Инфомация о портфеле {portfolio_info['accountId']} по состоянию на {datetime.fromtimestamp(portfolio_info['timestamp'] / 1000)}:\n\n"
        text_message += f"Объем активов: {portfolio_info['netAssetValue']} usd\n"
        text_message += f"Объем свободных средств: {portfolio_info['freeMoney']} usd\n\n"
        text_message += "Расшифровка активов:\n"

        # 5. Обрабатываем позиции
        for position in portfolio_info['positions']:
            print(f"Обработка позиции: {position['symbolId']}")
            share_record = find_share_record(case['case_name'], position['symbolId'])

            if share_record:
                print(f"Обновление записи для {position['symbolId']}")
                update_share_record(share_record, position)
                text_message += f"\n<b>{position['symbolId']}</b> - {position['quantity']} шт.\n"
                text_message += f"Цена тек.: {position['price']}\n"
                text_message += f"Цена позиц.: {position['averagePrice']}\n"
                text_message += f"PNL: {position['pnl']}, Объем: {position['value']}\n\n"
            else:
                print(f"Добавление новой записи для {position['symbolId']}")
                add_new_share_record(case['case_name'], position)
                text_message += f"\n<b> +++{position['symbolId']}</b> - {position['quantity']} шт.\n"
                text_message += f"Цена тек.: {position['price']}\n"
                text_message += f"Цена позиц.: {position['averagePrice']}\n"
                text_message += f"PNL: {position['pnl']}, Объем: {position['value']}\n\n"

    # 6. Обрабатываем записи с get_status = False
    inactive_shares = find_inactive_shares()
    print(f"Найдено неактивных записей: {inactive_shares.count()}")
    if inactive_shares:
        for share in inactive_shares:
            print(f"Обработка неактивной записи: {share['share']}")
            text_message += f"\n<b> ---{share['share']}</b> - {share['balance_count']} шт.\n"
            text_message += f"Объем: {share['balance_sum']}\n\n"
            reset_share_balance(share)

    print("Завершение выполнения process_get_status_message")
    return text_message

# Примерные функции для взаимодействия с базой данных и API
def select_active_cases():
    # Возвращает список активных записей из kogan_case
    # Здесь нужно реализовать логику для выборки данных из MongoDB
    pass

def reset_get_status_in_shares(case_names):
    # Устанавливает get_status = False для всех записей в kogan_case_share
    # Здесь нужно реализовать логику для обновления данных в MongoDB
    case_share_collection.update_many({"case_name": {"$in": case_names}}, {"$set": {"get_status": False}})

async def get_broker_info(account_id,application_id, application_access_key, api_url):
    # Делает асинхронный запрос к API брокера
    # Здесь нужно реализовать логику для выполнения HTTP-запроса
    try:
        response = requests.get(
            f"{api_url}3.0/summary/{account_id}/usd",
            auth=HTTPBasicAuth(application_id, application_access_key)
        )
        if response.status_code == 200:
            return response
        else:
            print(f"Ошибка при получении ответа от брокера: {response.text}")
            return None
    except Exception as e:
        print(f"Ошибка запроса к брокеру: {e}")
        return None

def find_share_record(case_name, symbol_id):
    # Находит запись в kogan_case_share по case_name и symbol_id
    # Здесь нужно реализовать логику для поиска данных в MongoDB
    return case_share_collection.find_one({"case_name": case_name, "share": symbol_id})


def update_share_record(share_record, position):
    # Обновляет запись в kogan_case_share
    # Здесь нужно реализовать логику для обновления данных в MongoDB
    case_share_collection.update_one(
        {"_id": share_record["_id"]},
        {"$set": position, "get_status": True}
    )
    if share_record['balance_count']!=position['quantity']:
        case_share_collection.update_one(
            {"_id": share_record["_id"]},
            {"$set": {"balance_count": position['quantity']}}
        )

def add_new_share_record(case_name, position):
    # Добавляет новую запись в kogan_case_share
    # Здесь нужно реализовать логику для добавления данных в MongoDB
    case_share_collection.insert_one(
        {"case_name": case_name, "share": position['symbolId'], "get_status": True, "balance_count": position['quantity'], "balance_sum": position['value']}
    )


def find_inactive_shares():
    # Находит все записи в kogan_case_share с get_status = False
    # Здесь нужно реализовать логику для поиска данных в MongoDB
    return case_share_collection.find({"get_status": False})

def reset_share_balance(share):
    # Обновляет баланс записи в kogan_case_share
    # Здесь нужно реализовать логику для обновления данных в MongoDB
    case_share_collection.update_one(
        {"_id": share["_id"]},
        {"$set": {"balance_sum": 0, "balance_count": 0}}
    )

# Пример вызова функций
# asyncio.run(process_set_signal_message("#set_signal\nPortfolio1, AAPL, BUY, 50\nPortfolio2, TSLA, SELL, 30"))
# asyncio.run(process_set_price_message())
# asyncio.run(process_set_new_message())
