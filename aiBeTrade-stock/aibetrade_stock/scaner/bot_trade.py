import os
import requests
import json
from requests.auth import HTTPBasicAuth
from telethon import TelegramClient, events
from pymongo import MongoClient
from datetime import datetime
from openai import OpenAI
import asyncio

# Настройки для OpenAI API
key = os.environ.get('OPENAI_API_KEY')
client_openai = OpenAI(api_key=key)

# Настройки для клиента Telethon
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
USER_PHONE = os.getenv('USER_PHONE')

# Инициализация клиента Telethon
client = TelegramClient('user_session_trade', API_ID, API_HASH)

# Подключение к MongoDB
mongo_url = os.getenv('MONGO_URL_SERV')
mongo_client = MongoClient(mongo_url)
db = mongo_client["nntcapital"]
signal_collection = db["kogan_signal"]
case_collection = db["kogan_case"]
case_share_collection = db["kogan_case_share"]
trading_collection = db["kogan_trading"]

# ID получателя в Telegram
recipient_id = '@igyak'

# Функция для отправки текста в ChatGPT и получения ответа
def send_to_chatgpt(prompt, text):
    try:
        message = f"Отправка в ChatGPT: Промт: {prompt}, Текст: {text}"
        print(message)
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
        message = f"Ошибка при отправке запроса в ChatGPT: {e}"
        print(message)
        asyncio.create_task(send_telegram_message(client, recipient_id, message))
        return None

# Функция для отправки ордера брокеру
def send_order_to_broker(symbol, side, quantity, account_id, application_id, application_access_key, api_url):
    message = f"Отправка ордера брокеру: {symbol} {side} {quantity}"
    print(message)
    asyncio.create_task(send_telegram_message(client, recipient_id, message))
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
        asyncio.create_task(send_telegram_message(client, recipient_id, error_message))
        return None, error_message
    except requests.exceptions.RequestException as e:
        error_message = f"Ошибка запроса: {e}"
        print(error_message)
        asyncio.create_task(send_telegram_message(client, recipient_id, error_message))
        return None, error_message

# Функция для отправки сообщения в Telegram
async def send_telegram_message(client, recipient_id, message):
    try:
        user_entity = await client.get_input_entity(recipient_id)
        await client.send_message(user_entity, message)
        print(f"Сообщение отправлено пользователю {recipient_id}: {message}")
    except Exception as e:
        print(f"Ошибка при отправке сообщения в Telegram: {e}")

# Функция для проверки статуса ордеров
async def check_order_status():
    while True:
        try:
            orders = trading_collection.find({"order_status": {"$nin": ["cancelled", "filled", "rejected"]}})
            for order in orders:
                order_id = order.get("orderId")
                case_name = order.get("case")

                case_info = case_collection.find_one({"case_name": case_name})
                if not case_info:
                    message = f"Информация о портфеле {case_name} не найдена."
                    print(message)
                    asyncio.create_task(send_telegram_message(client, recipient_id, message))
                    continue

                application_id = case_info.get("application_id")
                application_access_key = case_info.get("application_access_key")
                api_url = case_info.get("api_url")

                status_response = requests.get(
                    f"{api_url}/{order_id}",
                    auth=HTTPBasicAuth(application_id, application_access_key)
                )

                if status_response.status_code == 200:
                    order_status = status_response.json()["orderState"]["status"]

                    trading_collection.update_one(
                        {"orderId": order_id},
                        {
                            "$set": {
                                "order_status": order_status,
                                "order_details": status_response.json()
                            }
                        }
                    )

                    if order_status == "filled":
                        fills = status_response.json()["orderState"]["fills"]
                        total_quantity = sum(float(fill["quantity"]) for fill in fills)
                        total_sum = sum(float(fill["quantity"]) * float(fill["price"]) for fill in fills)
                        case = order["case"]
                        share = order["share"]

                        if status_response.json()["orderParameters"]["side"].upper() == "SELL":
                            total_quantity = -total_quantity
                            total_sum = -total_sum

                        share_info = case_share_collection.find_one({"case": case, "share": share})
                        if share_info:
                            balance_count = share_info.get("balance_count", 0) + total_quantity
                            balance_sum = 0 if balance_count == 0 else share_info.get("balance_sum", 0) + total_sum

                            case_share_collection.update_one(
                                {"case": case, "share": share},
                                {"$set": {"balance_count": balance_count, "balance_sum": balance_sum}}
                            )
                            message = f"Ордер {order_id} переведен в статус {order_status}. Информация в портфеле {case} обновлена для {share}"
                            print(message)
                            asyncio.create_task(send_telegram_message(client, recipient_id, message))
                        else:
                            case_share_collection.insert_one({
                                "case": case,
                                "share": share,
                                "balance_count": total_quantity,
                                "balance_sum": total_sum
                            })
                            message = f"Ордер {order_id} переведен в статус {order_status}. Новая запись создана для {share} в портфеле {case}"
                            print(message)
                            asyncio.create_task(send_telegram_message(client, recipient_id, message))
                else:
                    message = f"Ошибка при получении статуса ордера {order_id}: {status_response.text}"
                    print(message)
                    asyncio.create_task(send_telegram_message(client, recipient_id, message))

            await asyncio.sleep(10)

        except Exception as e:
            message = f"Ошибка при проверке статуса ордеров: {e}"
            print(message)
            asyncio.create_task(send_telegram_message(client, recipient_id, message))
            await asyncio.sleep(10)

# Функция для обработки сигналов с status_signal = new
async def process_new_signals():
    while True:
        try:
            signals = signal_collection.find({"status_signal": "new"})
            for signal in signals:
                case = signal["case_name"]
                share = signal["share"]
                type_op = signal["type"]
                price = signal["price"]
                balance = signal["balance"]
                signal_id = signal["_id"]

                case_info = case_collection.find_one({"case_name": case})
                if not case_info:
                    signal_collection.update_one({"_id": signal_id}, {"$set": {"status_signal": "error", "error_message": "Информация о портфеле не найдена."}})
                    message = f"Информация о портфеле {case} не найдена."
                    print(message)
                    asyncio.create_task(send_telegram_message(client, recipient_id, message))
                    continue

                account_id = case_info.get("account_id")
                application_id = case_info.get("application_id")
                application_access_key = case_info.get("application_access_key")
                api_url = case_info.get("api_url")
                case_deposit = case_info.get("case_deposit")
                active = case_info.get("active")

                if active:
                    case_share_info = case_share_collection.find_one({"case": case, "share": share})
                    balance_count = 0 if not case_share_info else case_share_info["balance_count"]
                    balance_sum = 0 if not case_share_info else case_share_info["balance_sum"]

                    if type_op == "BUY":
                        count_order = int((case_deposit * balance / 100) / price) if not case_share_info else int(((case_deposit * balance / 100) - balance_sum) / price)
                        sum = count_order * price
                    elif type_op == "SELL":
                        if not case_share_info:
                            message = "Позиция по акции не была сформирована ранее."
                            print(message)
                            asyncio.create_task(send_telegram_message(client, recipient_id, message))
                            continue
                        count_order = -balance_count if balance == 0 else int(balance_count * balance / 100)
                        sum = -balance_sum if balance == 0 else count_order * price

                    if balance_count + count_order < 0:
                        message = f"Количество акций {share} в портфеле {case} меньше чем размер ордера {count_order}. Действие не выполняется."
                        print(message)
                        asyncio.create_task(send_telegram_message(client, recipient_id, message))
                        continue

                    if count_order == 0:
                        message = f"Количество акций к покупке {count_order}. Действие не выполняется."
                        print(message)
                        asyncio.create_task(send_telegram_message(client, recipient_id, message))
                        continue

                    if count_order > 0:
                        broker_response, error_message = send_order_to_broker(share, type_op.lower(), abs(count_order), account_id, application_id, application_access_key, api_url)
                    else:
                        broker_response, error_message = send_order_to_broker(share, type_op.lower(), abs(count_order*(-1)), account_id, application_id, application_access_key, api_url)

                    if broker_response:
                        message = f"Успех! Ордер на {type_op} акции {share} в количестве {abs(count_order)} размещен успешно. {broker_response[0]['orderState']['status']}"
                        await send_telegram_message(client, recipient_id, message)

                        signal_collection.update_one({"_id": signal_id}, {"$set": {"status_signal": "complete", "order_details": broker_response, "error_message": None}})

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
                        signal_collection.update_one({"_id": signal_id}, {"$set": {"status_signal": "error", "error_message": error_message}})
                        await send_telegram_message(client, recipient_id, error_message)

            await asyncio.sleep(10)

        except Exception as e:
            message = f"Ошибка при обработке сигналов: {e}"
            print(message)
            asyncio.create_task(send_telegram_message(client, recipient_id, message))
            await asyncio.sleep(10)

# Обработка всех входящих сообщений
@client.on(events.NewMessage)
async def handle_incoming_message(event):
    message_text = event.raw_text
    if "#push" in message_text:
        process_push_message(message_text)

def process_push_message(message_text):
    message = f"Получено сообщение: {message_text}"
    print(message)
    asyncio.create_task(send_telegram_message(client, recipient_id, message))

    promt = (
        "Преобразуй сообщение в следующую структуру: "
        "Название портфеля без ковычек., "
        "Название акции: нужно найти по названию акцию и определить оптимальную биржу. Вернуть название акции вместе с биржей через точку. Например: AAPL.NASDAQ, "
        "Тип сигнала: BUY или SELL, Цена акции, Процент остатка акции в портфеле без знака процент. "
        "Дробные разделители точка. "
        "Структура должна включать в себя разделители данных {} и между разделителями данных не должно быть пробелов. "
        "Особенности сообщения. Иногда сообщение содержит информацию о продаже акции и не содержит ни процента продажи, "
        "ни процента остатка акций в портфеле это означает что продается все что есть и в этом случае процент остатка в портфеле будет 0. "
        "В финале проверить на соответствие полученного результата следующей структуре: "
        "{Название портфеля}{название акции}{тип сигнала}{Цена акции}{Процент остатка}. "
        "В случае, если исходное сообщение не содержит данных по указанной структуре, то данное сообщение игнорировать."
    )
    gpt_response = send_to_chatgpt(promt, message_text)

    if gpt_response:
        try:
            case, share, type_op, price, balance = gpt_response.strip('{}').split('}{')
            share = share.strip()
            price = float(price)
            balance = float(balance)
        except Exception as e:
            message = f"Ошибка при разборе ответа: {e}"
            print(message)
            asyncio.create_task(send_telegram_message(client, recipient_id, message))
            return

        signal_data = {
            "date": datetime.now(),
            "case_name": case,
            "share": share,
            "type": type_op,
            "price": price,
            "balance": balance,
            "status_signal": "new"
        }
        signal_id = signal_collection.insert_one(signal_data).inserted_id

        case_info = case_collection.find_one({"case_name": case})
        if not case_info:
            signal_collection.update_one({"_id": signal_id}, {"$set": {"status_signal": "error", "error_message": "Информация о портфеле не найдена."}})
            message = f"Информация о портфеле {case} не найдена."
            print(message)
            asyncio.create_task(send_telegram_message(client, recipient_id, message))
            return

        account_id = case_info.get("account_id")
        application_id = case_info.get("application_id")
        application_access_key = case_info.get("application_access_key")
        api_url = case_info.get("api_url")
        case_deposit = case_info.get("case_deposit")
        active = case_info.get("active")

        if active:
            case_share_info = case_share_collection.find_one({"case": case, "share": share})
            balance_count = 0 if not case_share_info else case_share_info["balance_count"]
            balance_sum = 0 if not case_share_info else case_share_info["balance_sum"]

            if type_op == "BUY":
                count_order = int((case_deposit * balance / 100) / price) if not case_share_info else int(((case_deposit * balance / 100) - balance_sum) / price)
                sum = count_order * price
            elif type_op == "SELL":
                if not case_share_info:
                    message = "Позиция по акции не была сформирована ранее."
                    print(message)
                    asyncio.create_task(send_telegram_message(client, recipient_id, message))
                    return
                count_order = -balance_count if balance == 0 else int(balance_count * balance / 100)
                sum = -balance_sum if balance == 0 else count_order * price

            if balance_count + count_order < 0:
                message = f"Количество акций {share} в портфеле {case} меньше чем размер ордера {count_order}. Действие не выполняется."
                print(message)
                asyncio.create_task(send_telegram_message(client, recipient_id, message))
                return

            if count_order == 0:
                message = f"Количество акций к покупке {count_order}. Действие не выполняется."
                print(message)
                asyncio.create_task(send_telegram_message(client, recipient_id, message))
                return

            if count_order > 0:
                broker_response, error_message = send_order_to_broker(share, type_op.lower(), abs(count_order), account_id, application_id, application_access_key, api_url)
            else:
                broker_response, error_message = send_order_to_broker(share, type_op.lower(), abs(count_order*(-1)), account_id, application_id, application_access_key, api_url)

            if broker_response:
                message = f"Успех! Ордер на {type_op} акции {share} в количестве {abs(count_order)} размещен успешно. {broker_response[0]['orderState']['status']}"
                asyncio.create_task(send_telegram_message(client, recipient_id, message))

                signal_collection.update_one({"_id": signal_id}, {"$set": {"status_signal": "complete", "order_details": broker_response, "error_message": None}})

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
                signal_collection.update_one({"_id": signal_id}, {"$set": {"status_signal": "error", "error_message": error_message}})
                asyncio.create_task(send_telegram_message(client, recipient_id, error_message))

# Запуск клиента и основных функций
async def main():
    await client.start(USER_PHONE)
    message = "Клиент Telegram запущен."
    print(message)
    asyncio.create_task(send_telegram_message(client, recipient_id, message))
    
    asyncio.create_task(check_order_status())
    asyncio.create_task(process_new_signals())
    
    await client.run_until_disconnected()

if __name__ == "__main__":
    client.loop.run_until_complete(main())
