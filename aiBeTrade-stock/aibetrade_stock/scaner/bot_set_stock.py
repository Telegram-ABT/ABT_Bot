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
case_collection = db["kogan_case"]
case_share_collection = db["kogan_case_share"]
trading_collection = db["kogan_trading"]

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

# Функция для получения текущей цены акции от брокера
def get_current_price(symbol, api_url, application_id, application_access_key):
    try:
        response = requests.get(
            f"{api_url}3.0/symbols/{symbol}",
            auth=HTTPBasicAuth(application_id, application_access_key)
        )
        response.raise_for_status()
        data = response.json()
        print(response)
        return data.get("optionData", {}).get("strikePrice")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении цены акции {symbol}: {e}")
        return None

# Функция для отправки ордера брокеру
def send_order_to_broker(symbol, side, quantity, account_id, application_id, application_access_key, api_url):
    print(f"Отправка ордера брокеру: {symbol} {side} {quantity}")
    order_data = {
        "accountId": account_id,
        "symbolId": symbol,
        "side": side,
        "quantity": str(quantity),
        "orderType": "market",
        "duration": "day"
    }

    response = requests.post(
        api_url,
        auth=HTTPBasicAuth(application_id, application_access_key),
        headers={'Content-Type': 'application/json'},
        data=json.dumps(order_data)
    )

    try:
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.HTTPError as e:
        error_message = f"ОШИБКА! Ордер на {side} акции {symbol} в количестве {quantity} не размещен. Ошибка: {response.text}"
        print(error_message)
        return None, error_message
    except requests.exceptions.RequestException as e:
        error_message = f"Ошибка запроса: {e}"
        print(error_message)
        return None, error_message

# Основная функция для обработки сообщений с #set_stocke
async def process_set_stocke_message(message_text):
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
        promt = f"Найди биржу, где торгуется акция {share}, и верни в формате Тикер.Биржа."
        gpt_response = send_to_chatgpt(promt, share)

        if gpt_response:
            share = gpt_response.strip()
            case_info = case_collection.find_one({"case_name": case})
            if not case_info:
                print(f"Информация о портфеле {case} не найдена.")
                continue

            account_id = case_info.get("account_id")
            application_id = case_info.get("application_id")
            application_access_key = case_info.get("application_access_key")
            api_url = case_info.get("api_url_date")
            case_deposit = case_info.get("case_deposit")
            active = case_info.get("active")

            if active:
                # Получение текущей цены акции
                price = get_current_price(share, api_url, application_id, application_access_key)
                if price is None:
                    print(f"Не удалось получить цену для акции {share}.")
                    continue

                case_share_info = case_share_collection.find_one({"case": case, "share": share})
                balance_count = 0 if not case_share_info else case_share_info["balance_count"]
                balance_sum = 0 if not case_share_info else case_share_info["balance_sum"]

                if type_op == "BUY":
                    count_order = int((case_deposit * balance / 100) / price) if not case_share_info else int(((case_deposit * balance / 100) - balance_sum) / price)
                    sum = count_order * price
                elif type_op == "SELL":
                    if not case_share_info:
                        print(f"Позиция по акции {share} не была сформирована ранее.")
                        continue
                    count_order = -balance_count if balance == 0 else int(balance_count * balance / 100)
                    sum = -balance_sum if balance == 0 else count_order * price

                if balance_count + count_order < 0:
                    print(f"Количество акций {share} в портфеле {case} меньше чем размер ордера {count_order}. Действие не выполняется.")
                    continue

                if count_order == 0:
                    print(f"Количество акций к покупке {count_order}. Действие не выполняется.")
                    continue

                if count_order > 0:
                    broker_response, error_message = send_order_to_broker(share, type_op.lower(), abs(count_order), account_id, application_id, application_access_key, api_url)
                else:
                    broker_response, error_message = send_order_to_broker(share, type_op.lower(), abs(count_order*(-1)), account_id, application_id, application_access_key, api_url)

                if broker_response:
                    print(f"Успех! Ордер на {type_op} акции {share} в количестве {abs(count_order)} размещен успешно. {broker_response[0]['orderState']['status']}")

                    trading_data = {
                        "date": datetime.now(),
                        "case": case,
                        "share": share,
                        "type": type_op,
                        "price": price,
                        "count_order": count_order,
                        "sum": sum,
                        "orderId": broker_response[0].get("orderId"),
                        "broker_response": broker_response,
                        "order_status": broker_response[0]["orderState"].get("status")
                    }
                    trading_collection.insert_one(trading_data)
                else:
                    print(error_message)

# Пример вызова функции
# asyncio.run(process_set_stocke_message("#set_stocke\nPortfolio1, AAPL, BUY, 50\nPortfolio2, TSLA, SELL, 30"))
